"""History for the in-game addon -> WTF/Account/<acct>/SavedVariables/ForeverMarketData.lua."""
import os
import re
from datetime import datetime, timezone

from fm import addon_files, history, paths, report

ADDON = "ForeverMarketUI"
MAX_POINTS = 168          # hourly points kept for tier 1 (one week)
DAILY_POINTS = 90         # daily points kept for tier 2 (one quarter)
TOP_API = 500             # tier 1 = this many items by cheapest listing
MAX_BYTES = 3_000_000     # hard cap on the generated Lua


def lua(v):
    if isinstance(v, dict):
        return "{" + ",".join((k if re.fullmatch(r"[A-Za-z_]\w*", k) else f"[{lua(k)}]") + "=" + lua(x)
                              for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "{" + ",".join(map(lua, v)) + "}"
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    return str(round(v, 2) if isinstance(v, float) else v)


def _unix(at):
    return int(datetime.fromisoformat(at).timestamp())


def _known(d):
    return {k: v for k, v in d.items() if v is not None}  # unknown stays nil, never 0


def _cheapest_by_region(conn, house, region):
    """item -> {region: copper}; the home region counts only the picked house."""
    latest = dict(conn.execute(
        "SELECT region, MAX(at) FROM price_history WHERE source = 'api' GROUP BY region"))
    cheapest = {}
    for reg, at in sorted(latest.items()):
        for item, lo in conn.execute(
                """SELECT item_id, MIN(min_buyout) FROM price_history
                   WHERE source = 'api' AND region = ? AND at = ? AND (region != ? OR house_id = ?)
                   GROUP BY item_id""", (reg, at, region, house)):
            cheapest.setdefault(item, {})[reg] = lo
    return cheapest


def _series(conn, ids, house, region, daily):
    """item -> {at: point}. daily=True keeps only the last row of each day."""
    sql = """SELECT item_id, at, source, min_buyout, market, listings, qty FROM price_history
             JOIN export_ids ON id = item_id
             WHERE region = ? AND ((source = 'tsm' AND house_id = ?) OR (source = 'api' AND house_id = ?))"""
    if daily:
        sql = f"""SELECT item_id, at, source, min_buyout, market, listings, qty FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY item_id, substr(at, 1, 10) ORDER BY at DESC) rn
                    FROM ({sql})) WHERE rn = 1"""
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS export_ids (id INTEGER PRIMARY KEY)")
    conn.execute("DELETE FROM export_ids")
    conn.executemany("INSERT INTO export_ids VALUES (?)", [(i,) for i in ids])
    out = {}
    for item, at, source, lo, market, listings, qty in conn.execute(
            sql + " ORDER BY item_id, at, source DESC", (region, history.TSM_HOUSE, house)
            if not daily else (region, history.TSM_HOUSE, house)):
        p = out.setdefault(item, {}).setdefault(at, {"t": _unix(at)})
        p.update(_known({"typical": market, "cheapest": lo, "qty": qty, "auctions": listings}))
    return out


def build(conn, now=None):
    house, _ = report.pick_house(conn)
    r = conn.execute("SELECT region FROM api_house WHERE house_id = ?", (house,)).fetchone()
    region = r[0] if r else "us"
    cheapest = _cheapest_by_region(conn, house, region)
    priced = sorted((i for i in cheapest if region in cheapest[i] and cheapest[i][region] > 0),
                    key=lambda i: (-cheapest[i][region], i))
    dropped = [r[0] for r in conn.execute(
        "SELECT DISTINCT item_id FROM loot_item_source WHERE item_id IS NOT NULL ORDER BY 1")]
    tier1 = priced[:TOP_API]
    tier2 = [i for i in priced[TOP_API:] if i not in set(tier1)]
    # measured drops always ship, at hourly resolution, even when their price is unknown
    extras = [i for i in dropped if i not in set(tier1)]

    tier1_series = _series(conn, tier1 + extras, house, region, daily=False)
    tier2_series = _series(conn, tier2, house, region, daily=True)

    sold = {r["item_id"]: {"q": r["q"], "n": r["n"], "t": r["t"]} for r in conn.execute(
        """SELECT item_id, SUM(quantity) AS q, COUNT(*) AS n, SUM(buyout) AS t
           FROM auction_life WHERE sold = 1 GROUP BY item_id""")}
    mine = {r["item_id"]: {"n": r["n"], "u": r["u"]} for r in conn.execute(
        """SELECT item_id, COUNT(*) AS n, CAST(AVG(unit) AS INTEGER) AS u
           FROM trade WHERE kind = 'sale' GROUP BY item_id""")}
    meta = {r[0]: r[1:] for r in conn.execute(
        "SELECT id, name, quality, item_level, vendor_sell, class_id, sub_class FROM item")}

    def make(i, series, res, window):
        n, q, il, vendor, c, s = meta.get(i, (None,) * 6)
        return _known({"n": n, "q": q, "il": il, "vendor": vendor, "c": c, "s": s, "res": res,
                       "sold": sold.get(i), "my": mine.get(i),
                       "series": [series[i][at] for at in sorted(series.get(i, {}))][-window:]})

    items, size, skipped = {}, 200_000, 0
    for i in tier1 + extras:
        entry = make(i, tier1_series, "h", MAX_POINTS)
        blob = len(lua(entry))
        items[f"i:{i}"] = entry
        size += blob
    for i in tier2:  # cheapest first out of the file when over the cap
        entry = make(i, tier2_series, "d", DAILY_POINTS)
        blob = len(lua(entry))
        if size + blob > MAX_BYTES:
            skipped += 1
            continue
        items[f"i:{i}"] = entry
        size += blob

    indices = {}
    for at, cat, v in conn.execute("SELECT at, category, index_value FROM index_history ORDER BY category, at"):
        indices.setdefault(cat, []).append({"t": _unix(at), "v": v})
    stamp = now or datetime.now(timezone.utc)
    data = _known({"generated": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "generated_ts": int(stamp.timestamp()),
                   "next_update": int(stamp.timestamp()) + 3600,
                   "house": house, "region": region,
                   "indices": {c: p[-MAX_POINTS:] for c, p in indices.items()}, "items": items})
    return data, {"tier1": len(tier1), "extras": len(extras), "tier2": len(items) - len(tier1) - len(extras),
                  "skipped": skipped, "priced": len(priced)}


def to_lua(data):
    head = {k: v for k, v in data.items() if k != "items"}
    lines = ["ForeverMarketData = {"] + [f"{k}={lua(v)}," for k, v in head.items()] + ["items={"]
    lines += [f"[{lua(k)}]={lua(v)}," for k, v in data["items"].items()]
    return "\n".join(lines + ["},", "}", ""])


def run(conn, client_dir=paths.CLIENT_DIR):
    data, stats = build(conn)
    text = to_lua(data)
    path = addon_files.write(addon_files.path(ADDON, client_dir=client_dir), text)
    points = sum(len(v["series"]) for v in data["items"].values())
    print(f"items {len(data['items'])} (hourly {stats['tier1'] + stats['extras']}, daily {stats['tier2']}, "
          f"skipped for size {stats['skipped']} of {stats['priced']} priced), series points {points}, "
          f"bytes {len(text.encode())} -> {path} (the game can be open; /reload picks it up)")
    if len(text.encode()) > MAX_BYTES:
        print(f"warning: {len(text.encode())} bytes is over the {MAX_BYTES} cap")
    return 0
