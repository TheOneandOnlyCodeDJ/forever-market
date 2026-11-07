"""Builds reports/digest.md and data/summary.json from the DB alone (no network)."""
import json
import statistics
from datetime import datetime, timezone

from fm.db import ROOT
from fm.fmt import coin, gold, num, pct

SUBCLASS = {5: "Cloth", 6: "Leather", 9: "Herb", 10: "Elemental", 7: "Ore/Stone", 8: "Meat",
            12: "Enchanting", 11: "Other", 1: "Parts"}
NODE_YIELD = {9: 1.5, 7: 2.2, 6: 1.0, 5: 1.0}  # classic yield per node, by Trade Goods subclass
TABLES = ["item", "price_realm", "price_region", "spell", "spell_reagent", "craft_output",
          "creature", "area", "drop", "kill_event", "loot_event", "node_area", "sync_log",
          "loot_session", "loot_source", "loot_item_source", "loot_item"]
COPPER = {"market", "minBO", "historical", "gap", "node value", "value", "cost", "sell", "profit", "copper",
          "copper/kill", "loot/kill", "total/kill"}
NAME = "COALESCE(i.name, 'item ' || p.item_id)"


def _fmt(col, v):
    if col in COPPER:
        return ("0.00g" if v == 0 else gold(v)) if col in ("profit", "copper") else (
            coin(v) if col.endswith("/kill") else gold(v))
    if col.endswith("%") or col in ("rate", "loot share"):
        return pct(v)
    if col in ("region sale", "sale rate"):
        return "-" if v is None else f"{v:.3f}"
    return num(v)


def _table(cols, rows):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(_fmt(c, r[c]) for c in cols) + " |" for r in rows]
    return out + ["", f"rows: {len(rows)}", ""]


def craft(conn):
    """Cheapest fully priced spell per output item -> (rows sorted by profit, skipped counts)."""
    realm = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT item_id, market_value, min_buyout FROM price_realm")}
    region = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT item_id, market_value, sale_rate FROM price_region")}
    names = dict(conn.execute("SELECT id, name FROM item"))
    reagents = {}
    for spell, item, qty in conn.execute("SELECT spell_id, item_id, quantity FROM spell_reagent"):
        reagents.setdefault(spell, []).append((item, qty))
    best, seen = {}, set()
    for spell, item, n, prof, skill in conn.execute(
            """SELECT c.spell_id, c.item_id, c.num_result, s.profession, s.min_skill
               FROM craft_output c JOIN spell s ON s.id = c.spell_id ORDER BY c.spell_id"""):
        seen.add(item)
        cost, realm_only = 0, True
        for mat, qty in reagents.get(spell, []):
            price = (realm.get(mat) or (None,))[0] or None
            if price is None:
                realm_only = False
                price = (region.get(mat) or (None,))[0] or None
            if price is None:
                break
            cost += qty * price
        else:
            cost = round(cost / (n or 1))  # per crafted item
            if item not in best or cost < best[item][0]:
                best[item] = (cost, prof + ("" if realm_only else "*"), skill)
    rows, no_sell = [], 0
    for item, (cost, prof, skill) in best.items():
        market, min_bo = realm.get(item, (None, None))
        if not market:
            no_sell += 1  # listed in WATCH instead
            continue
        sell = round(0.95 * market)
        profit = sell - cost
        listed = "yes" if (min_bo or 0) > 0 else "no"
        name = names.get(item) or f"item {item}"
        rows.append({"item": ("HIDDEN " if profit > 0 and listed == "no" else "") + name,
                     "profession": prof, "skill": skill, "cost": cost, "sell": sell,
                     "profit": profit, "margin %": round(100 * profit / cost, 1) if cost else None,
                     "listed": listed, "sale rate": (region.get(item) or (None, None))[1]})
    rows.sort(key=lambda r: (-r["profit"], r["item"]))
    return rows[:30], {"priced": len(best), "unpriced mats": len(seen - best.keys()),
                       "no realm price": no_sell}


LATEST = """SELECT id FROM loot_session s WHERE started = (
               SELECT MAX(started) FROM loot_session WHERE character = s.character)"""
RATES = f"""SELECT r.session_id, r.source_name AS source, r.item_id, src.kills, r.count AS drops,
              ROUND(100.0 * r.count / src.kills, 1) AS rate,
              COALESCE(li.name, i.name, 'item ' || r.item_id) AS item
            FROM loot_item_source r
            JOIN loot_source src ON src.session_id = r.session_id AND src.name = r.source_name
            LEFT JOIN loot_item li ON li.session_id = r.session_id AND li.item_id = r.item_id
            LEFT JOIN item i ON i.id = r.item_id
            WHERE r.session_id IN ({LATEST}) AND src.kills > 0"""


def price_of(conn, item_id):
    """(copper, 'realm'|'region') from market_value, or (None, 'none'). TSM's 0 means no data."""
    for table, source in (("price_realm", "realm"), ("price_region", "region")):
        r = conn.execute(f"SELECT market_value FROM {table} WHERE item_id = ?", (item_id,)).fetchone()
        if r and r[0]:
            return r[0], source
    return None, "none"


def _loot(conn, session_id, source):
    """Per item of one source: [(item, rate, drops, copper value or None)]."""
    return [(r["item"], r["rate"], r["drops"], (lambda c: c and c * r["drops"])(price_of(conn, r["item_id"])[0]))
            for r in conn.execute(RATES + " AND r.session_id = ? AND r.source_name = ?", (session_id, source))]


def kill(conn):
    """Measured loot from the most recent session per character -> (KILL rows, MEASURED rows, footer)."""
    best = {}
    for r in conn.execute(RATES + " ORDER BY rate DESC, r.item_id"):
        best.setdefault((r["session_id"], r["source"]), r)
    rows = []
    for r in conn.execute(f"""SELECT session_id, name, kills, copper FROM loot_source
                              WHERE session_id IN ({LATEST}) AND kills >= 5
                              ORDER BY kills DESC, name"""):
        labelled = r["name"] != "Unknown creature"
        b = best.get((r["session_id"], r["name"])) if labelled else None
        loot = _loot(conn, r["session_id"], r["name"])
        loot_kill = round(sum(v or 0 for *_, v in loot) / r["kills"])  # unpriced drops count as 0
        per_kill = round(r["copper"] / r["kills"]) if r["copper"] is not None else None
        rows.append({"source": r["name"], "kills": r["kills"], "copper": r["copper"],
                     "copper/kill": per_kill, "loot/kill": loot_kill,
                     "total/kill": None if per_kill is None else per_kill + loot_kill,
                     "best item": b["item"] if b else None, "rate": b["rate"] if b else None,
                     "sample": r["kills"], "session": r["session_id"], "_loot": loot,
                     "unpriced drops": sum(d for _, _, d, v in loot if v is None)})
    measured = [{"item": r["item"], "source": r["source"], "kills": r["kills"], "drops": r["drops"],
                 "rate %": r["rate"]} for r in conn.execute(
        RATES + " AND src.kills >= 20 AND r.count >= 2 AND src.name != 'Unknown creature'"
        " ORDER BY rate DESC, src.kills DESC, item LIMIT 25")]
    footer = dict(conn.execute("""SELECT COUNT(*) AS sessions, COUNT(DISTINCT character) AS characters,
                                  SUM(kills) AS kills FROM loot_session""").fetchone())
    footer["unpriced drops"] = sum(r["unpriced drops"] for r in rows)
    return rows, measured, footer


def farm(conn, kill_rows):
    """KILL rows with kills >= 10 ranked by total/kill -> (FARM rows, pace per session, footer)."""
    labelled = [r for r in kill_rows if r["source"] != "Unknown creature"]  # not a farmable target
    rows = []
    for r in labelled:
        if r["kills"] < 10:
            continue
        value = sum(v or 0 for *_, v in r["_loot"])
        best = max(r["_loot"], key=lambda x: (x[3] or 0, x[1]), default=None)
        drops = sum(d for _, _, d, _ in r["_loot"])
        rows.append({"source": r["source"], "kills": r["kills"], "copper/kill": r["copper/kill"],
                     "loot/kill": r["loot/kill"], "total/kill": r["total/kill"],
                     "loot share": round(100 * (best[3] or 0) / value, 1) if value else None,
                     "best item": best[0] if best else None, "rate": best[1] if best else None,
                     "confidence": "ok" if r["kills"] >= 50 else "thin", "session": r["session"],
                     "drops": drops, "priced drops": drops - r["unpriced drops"]})
    rows.sort(key=lambda r: (-(r["total/kill"] if r["total/kill"] is not None else -1), r["source"]))
    rows = rows[:25]
    pace = []
    for sid in dict.fromkeys(r["session"] for r in rows):
        s = conn.execute("SELECT character, kills, copper, seconds FROM loot_session WHERE id = ?", (sid,)).fetchone()
        items = sum((price_of(conn, i)[0] or 0) * n for i, n in conn.execute(
            "SELECT item_id, count FROM loot_item WHERE session_id = ?", (sid,)))
        value = (s["copper"] or 0) + items
        hours = s["seconds"] / 3600 if s["seconds"] else None
        pace.append({"session": sid, "character": s["character"], "seconds": s["seconds"],
                     "kills": s["kills"], "loot value": value,
                     "kills/hour": round(s["kills"] / hours, 1) if hours and s["kills"] is not None else None,
                     "copper/hour": round(value / hours) if hours else None})
    drops = sum(r["drops"] for r in rows)
    footer = {"considered": len(labelled), "low sample": sum(r["kills"] < 10 for r in labelled),
              "unlabelled excluded": len(kill_rows) - len(labelled), "drops": drops,
              "priced drops": sum(r["priced drops"] for r in rows),
              "price coverage %": round(100 * sum(r["priced drops"] for r in rows) / drops, 1) if drops else None}
    return rows, pace, footer


def status(conn):
    """Latest sync_log row per source and row count per table."""
    sources = [dict(r) for r in conn.execute("""SELECT source, fetched_at, rows, note FROM sync_log s
                   WHERE rowid = (SELECT MAX(rowid) FROM sync_log WHERE source = s.source)
                   ORDER BY source""")]
    counts = [{"table": t, "rows": conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]}
              for t in TABLES]
    return sources, counts


def build(conn):
    q = lambda sql: [dict(r) for r in conn.execute(sql)]
    sources, counts = status(conn)

    values = [r[0] for r in conn.execute("SELECT market_value FROM price_realm WHERE market_value > 0")]
    listed = [r[0] for r in conn.execute("SELECT min_buyout FROM price_realm WHERE min_buyout > 0")]
    median = int(statistics.median(values)) if values else None
    snapshot = [
        {"metric": "realm items with market value", "value": len(values), "unit": "count"},
        {"metric": "sum market value", "value": sum(values) or None, "unit": "copper"},
        {"metric": "median market value", "value": median, "unit": "copper"},
        {"metric": "items with market value >= 10g", "value": sum(v >= 100000 for v in values), "unit": "count"},
        {"metric": "realm items listed (minBO > 0)", "value": len(listed), "unit": "count"},
        {"metric": "sum minBO, 1 unit each", "value": sum(listed) or None, "unit": "copper"},
    ]
    movers = q(f"""SELECT {NAME} AS item, p.market_value AS market, p.historical,
                   ROUND(100.0 * (p.market_value - p.historical) / p.historical, 1) AS "change %"
                   FROM price_realm p LEFT JOIN item i ON i.id = p.item_id
                   WHERE p.market_value >= 10000 AND p.historical >= 5000
                   ORDER BY ABS(p.market_value - p.historical) * 1.0 / p.historical DESC, p.item_id
                   LIMIT 10""")
    gather = q(f"""SELECT {NAME} AS item, i.sub_class, p.market_value AS market,
                   p.min_buyout AS minBO, g.sale_rate AS "region sale"
                   FROM price_realm p JOIN item i ON i.id = p.item_id
                   LEFT JOIN price_region g ON g.item_id = p.item_id
                   LEFT JOIN craft_output c ON c.item_id = p.item_id
                   WHERE i.class_id = 7 AND p.market_value > 0 AND c.item_id IS NULL""")
    # also drop processed goods by name in case recipes were never synced
    PROCESSED = (" bar", "bolt of", "grinding stone", " thread", " rod")
    gather = [r for r in gather if not r["item"].lower().endswith(PROCESSED)
              and not r["item"].lower().startswith("bolt of")]
    for r in gather:
        sub = r.pop("sub_class")
        r["type"] = SUBCLASS.get(sub, f"sub {sub}")
        r["node value"] = round(r["market"] * NODE_YIELD[sub]) if sub in NODE_YIELD else None
    gather.sort(key=lambda r: (-(r["node value"] or 0), -r["market"], r["item"]))
    flip = q(f"""SELECT {NAME} AS item, p.market_value AS market, p.min_buyout AS minBO,
                 p.market_value - p.min_buyout AS gap,
                 ROUND(100.0 * (p.market_value - p.min_buyout) / p.market_value, 1) AS "gap %"
                 FROM price_realm p LEFT JOIN item i ON i.id = p.item_id
                 WHERE p.market_value >= 10000 AND p.min_buyout > 0
                   AND p.min_buyout <= 0.7 * p.market_value
                 ORDER BY gap DESC, p.item_id LIMIT 25""")
    watch = q("""SELECT COALESCE(i.name, 'item ' || w.item_id) AS item, group_concat(DISTINCT w.why) AS reason
                 FROM (SELECT item_id, 'recipe output' AS why FROM craft_output
                       UNION SELECT item_id, 'drop' FROM "drop") w
                 LEFT JOIN item i ON i.id = w.item_id
                 LEFT JOIN price_realm p ON p.item_id = w.item_id
                 WHERE COALESCE(p.market_value, 0) = 0
                 GROUP BY w.item_id ORDER BY item LIMIT 50""")
    watch_total = conn.execute("""SELECT COUNT(*) FROM (SELECT item_id FROM craft_output
                                  UNION SELECT item_id FROM "drop")""").fetchone()[0]
    craft_rows, craft_skipped = craft(conn)
    kill_rows, measured, kill_totals = kill(conn)
    farm_rows, farm_pace, farm_totals = farm(conn, kill_rows)
    for r in kill_rows:
        del r["_loot"]
    return {"sources": sources, "counts": counts, "snapshot": snapshot, "movers": movers,
            "gather": gather, "kill": kill_rows, "measured": measured, "kill_totals": kill_totals,
            "farm": farm_rows, "farm_pace": farm_pace, "farm_totals": farm_totals,
            "craft": craft_rows, "craft_skipped": craft_skipped,
            "flip": flip, "watch": watch, "watch_total": watch_total}


COLUMNS = {
    "sources": ["source", "fetched_at", "rows", "note"],
    "counts": ["table", "rows"],
    "movers": ["item", "market", "historical", "change %"],
    "gather": ["item", "type", "market", "minBO", "region sale", "node value"],
    "craft": ["item", "profession", "skill", "cost", "sell", "profit", "margin %", "listed", "sale rate"],
    "kill": ["source", "kills", "copper", "copper/kill", "loot/kill", "total/kill", "best item", "rate", "sample"],
    "farm": ["source", "kills", "total/kill", "loot share", "best item", "rate", "confidence"],
    "measured": ["item", "source", "kills", "drops", "rate %"],
    "flip": ["item", "market", "minBO", "gap", "gap %"],
    "watch": ["item", "reason"],
}


def _kill_lines(data):
    t = data["kill_totals"]
    if not t["sessions"]:
        return ["no loot data yet", "", "rows: 0", ""]
    return ["measured loot (Loot Tracker Forever), most recent session per character, sources with "
            "kills >= 5. copper = looted coin only. best item = highest drops/kills; rate in percent; "
            "sample = kills. loot/kill = sum(drops x price) / kills, price = realm market, else region "
            "market, else 0. total/kill = copper/kill + loot/kill.", "", *_table(COLUMNS["kill"], data["kill"]),
            f"sessions imported: {t['sessions']}, characters: {t['characters']}, total kills: {t['kills']}, "
            f"drops with no price (counted as 0): {t['unpriced drops']}", "",
            "### MEASURED", "", "kills >= 20 and drops >= 2; top 25 by rate.", "",
            *_table(COLUMNS["measured"], data["measured"]),
            "measured rates are local to this realm and character", ""]


def _farm_lines(data):
    t = data["farm_totals"]
    pace = [f"pace: {p['kills/hour'] if p['kills/hour'] is not None else '-'} kills/hour, "
            f"{gold(p['copper/hour'])}/hour (gold/hour) from session {p['session']} ({p['character']}), "
            f"ran {p['seconds'] // 60 if p['seconds'] else '-'} min, {p['kills']} kills, "
            f"loot value {gold(p['loot value'])} = coin + all looted items x price" for p in data["farm_pace"]]
    return [*(pace or ["pace: - (no FARM rows)"]), "",
            "sources with kills >= 10 from the KILL table, by total/kill, cap 25. best item = largest share "
            "of loot value; loot share = percent of the source's loot value from it; rate = its drops/kills "
            "in percent. confidence: ok at kills >= 50, thin at 10-49.", "",
            *_table(COLUMNS["farm"], data["farm"]),
            f"sources considered: {t['considered']}, dropped for low sample (kills < 10): {t['low sample']}, "
            f"unlabelled excluded: {t['unlabelled excluded']}, price coverage: {pct(t['price coverage %'])} "
            f"({t['priced drops']}/{t['drops']} drops priced)", ""]


def render(data, generated_at):
    snap = [{"metric": r["metric"], "value": gold(r["value"]) if r["unit"] == "copper" else num(r["value"])}
            for r in data["snapshot"]]
    lines = ["# forever-market digest", "", f"generated_at: {generated_at}", "",
             "Prices in gold (g). `-` = unknown. `region sale` is a 0-1 rate. "
             "`note` holds TSM updatedAt or the wago build.", "",
             "## Sources", "", *_table(COLUMNS["sources"], data["sources"]),
             "## Row counts", "", *_table(COLUMNS["counts"], data["counts"]),
             "## SNAPSHOT", "", "| metric | value |", "|---|---|",
             *[f"| {r['metric']} | {r['value']} |" for r in snap], "", f"rows: {len(snap)}", "",
             "### Movers vs historical (market >= 1g)", "", *_table(COLUMNS["movers"], data["movers"]),
             "## GATHER", "",
             "node value = market x classic yield (herb 1.5, ore 2.2, leather/cloth 1.0).", "",
             *_table(COLUMNS["gather"], data["gather"]),
             "## KILL", "", *_kill_lines(data),
             "## FARM", "", *_farm_lines(data),
             "## CRAFT", "",
             "cost = sum(qty x mat price) / items per craft, realm price first; `*` after profession = "
             "some mat priced from region. sell = 0.95 x realm market. margin % = 100 x profit / cost. "
             "HIDDEN = profit > 0 and nothing listed. sale rate is region, 0-1. Top 30 by profit.", "",
             *_table(COLUMNS["craft"], data["craft"]),
             "skipped: {unpriced mats} outputs with unpriced materials, {no realm price} with no realm "
             "market value (see WATCH); {priced} outputs fully priced.".format(**data["craft_skipped"]), "",
             "## FLIP", "", "realm items, market >= 1g, minBO <= 0.7 x market; top 25 by gap.", "",
             *_table(COLUMNS["flip"], data["flip"]),
             "## WATCH", "",
             f"recipe outputs or drops with no realm price; showing {len(data['watch'])} "
             f"of {data['watch_total']}.", "",
             *_table(COLUMNS["watch"], data["watch"])]
    return "\n".join(lines)


def run(conn, md_path=ROOT / "reports" / "digest.md", json_path=ROOT / "data" / "summary.json"):
    data = build(conn)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render(data, generated_at))
    meta = {
        "generated_at": generated_at,
        "units": "every money field is copper (integer); 'region sale' is a 0-1 rate; "
                 "fields ending in '%' are percent 0-100; null = unknown",
        "keys": {
            "sources": "latest sync_log row per source; note = TSM updatedAt, wago build, or FAILED reason",
            "counts": "row count per DB table",
            "snapshot": "metric, value, unit (copper|count)",
            "movers": "realm market vs historical, top 10 by |change %|",
            "gather": "Trade Goods (class 7) with realm price; node value = market x yield",
            "craft": "cheapest fully priced spell per output; cost per crafted item; sell = 0.95 x realm "
                     "market; '*' in profession = a mat priced from region; HIDDEN = profit > 0, not listed; cap 30",
            "craft_skipped": "priced = outputs with every mat priced; unpriced mats / no realm price = skipped",
            "kill": "loot_source rows with kills >= 5 from the latest session per character; copper fields "
                    "copper; rate = best item drops/kills as percent 0-100; sample = kills",
            "measured": "per item+source, kills >= 20 and drops >= 2, top 25 by rate %",
            "kill_totals": "all imported loot sessions: sessions, characters, kills; unpriced drops in KILL rows",
            "farm": "KILL rows with kills >= 10 (no 'Unknown creature') by total/kill, cap 25; copper/kill, "
                    "loot/kill, total/kill copper; loot share percent 0-100 of loot value from best item",
            "farm_pace": "per session behind FARM rows: seconds, kills, loot value (coin + items, copper), "
                         "kills/hour, copper/hour",
            "farm_totals": "considered, low sample, unlabelled excluded, drops, priced drops, price coverage %",
            "flip": "market >= 10000 copper, minBO <= 0.7 x market, sorted by gap, cap 25",
            "watch": "recipe outputs / drops with no realm price",
        },
        "columns": COLUMNS,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({"_meta": meta, **data}, indent=1))
    print(f"wrote {md_path} and {json_path}: " + ", ".join(
        f"{k} {len(data[k])}" for k in ("snapshot", "movers", "gather", "kill", "measured", "farm", "craft", "flip", "watch")))
    return data
