"""History for the in-game addon -> WTF/Account/<acct>/SavedVariables/ForeverMarketData.lua."""
import os
import re
from datetime import datetime, timezone

from fm import export_tsm, history, paths, report

FILE = "ForeverMarketData.lua"
PENDING = "ForeverMarketData.pending.lua"
MAX_ITEMS, MAX_POINTS, TOP_API, SOFT_BYTES = 2000, 168, 300, 2_000_000


def game_running():
    if os.environ.get("FM_FORCE_GAME_RUNNING") == "1":
        return True
    if os.environ.get("FM_FORCE_GAME_CLOSED") == "1":
        return False
    return export_tsm.game_running()


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


def build(conn, now=None):
    house, _ = report.pick_house(conn)
    r = conn.execute("SELECT region FROM api_house WHERE house_id = ?", (house,)).fetchone()
    region = r[0] if r else "us"
    latest = dict(conn.execute("SELECT region, MAX(at) FROM price_history WHERE source = 'api' GROUP BY region"))
    cheapest = {}  # item -> {region: copper}; the home region counts only the picked house
    for reg, at in sorted(latest.items()):
        for item, lo in conn.execute(
                """SELECT item_id, MIN(min_buyout) FROM price_history WHERE source = 'api' AND region = ? AND at = ?
                   AND (region != ? OR house_id = ?) GROUP BY item_id""", (reg, at, region, house)):
            cheapest.setdefault(item, {})[reg] = lo
    top = sorted((i for i in cheapest if region in cheapest[i]), key=lambda i: (-cheapest[i][region], i))[:TOP_API]
    dropped = [r[0] for r in conn.execute(
        "SELECT DISTINCT item_id FROM loot_item_source WHERE item_id IS NOT NULL ORDER BY 1")]
    ids = sorted(list(dict.fromkeys(top + dropped))[:MAX_ITEMS])  # top api first, so the cap trims drops

    series = {i: {} for i in ids}
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS export_ids (id INTEGER PRIMARY KEY)")
    conn.execute("DELETE FROM export_ids")
    conn.executemany("INSERT INTO export_ids VALUES (?)", [(i,) for i in ids])
    # shortcut: scans all of price_history each run, add an (item_id, at) index or prune rows when it gets slow
    for item, at, source, lo, market, listings, qty in conn.execute(
            """SELECT item_id, at, source, min_buyout, market, listings, qty FROM price_history
               JOIN export_ids ON id = item_id
               WHERE region = ? AND (source = 'tsm' AND house_id = ? OR source = 'api' AND house_id = ?)
               ORDER BY source DESC""", (region, history.TSM_HOUSE, house)):  # tsm first, api overrides cheapest
        p = series[item].setdefault(at, {"t": _unix(at)})
        p.update(_known({"typical": market, "cheapest": lo, "qty": qty, "auctions": listings}))
    meta = {r[0]: r[1:] for r in conn.execute(
        "SELECT id, name, quality, item_level, vendor_sell, class_id, sub_class FROM item JOIN export_ids USING (id)")}
    items = {}
    for i in ids:
        n, q, il, vendor, c, s = meta.get(i, (None,) * 6)
        items[f"i:{i}"] = _known({"n": n, "q": q, "il": il, "vendor": vendor, "c": c, "s": s,
                                  "regions": cheapest.get(i),
                                  "series": [series[i][at] for at in sorted(series[i])][-MAX_POINTS:]})
    indices = {}
    for at, cat, v in conn.execute("SELECT at, category, index_value FROM index_history ORDER BY category, at"):
        indices.setdefault(cat, []).append({"t": _unix(at), "v": v})
    return _known({"generated": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "house": house, "region": region,
                   "indices": {c: p[-MAX_POINTS:] for c, p in indices.items()}, "items": items})


def to_lua(data):
    head = {k: v for k, v in data.items() if k != "items"}
    lines = ["ForeverMarketData = {"] + [f"{k}={lua(v)}," for k, v in head.items()] + ["items={"]
    lines += [f"[{lua(k)}]={lua(v)}," for k, v in data["items"].items()]
    return "\n".join(lines + ["},", "}", ""])


def run(conn, client_dir=paths.CLIENT_DIR):
    path = export_tsm.target(client_dir).with_name(FILE)
    pending = path.with_name(PENDING)
    data = build(conn)
    text = to_lua(data).encode()
    points = sum(len(v["series"]) for v in data["items"].values())
    if game_running():
        pending.write_bytes(text)
        print(f"Wow.exe is running: wrote {pending.name}, it will be promoted on the next run with the game closed")
        dest, promoted = pending, False
    else:
        promoted = pending.exists()
        if promoted:
            pending.replace(path)
        path.write_bytes(text)
        dest = path
    print(f"items {len(data['items'])}, series points {points}, bytes {len(text)}, "
          f"promoted pending: {'yes' if promoted else 'no'} -> {dest}")
    if len(text) > SOFT_BYTES:
        print(f"warning: {len(text)} bytes is over the 2 MB target")
    return 0
