"""Builds reports/digest.md and data/summary.json from the DB alone (no network)."""
import json
import statistics
from datetime import datetime, timezone

from fm.db import ROOT
from fm.fmt import gold, num, pct

SUBCLASS = {5: "Cloth", 6: "Leather", 9: "Herb", 10: "Elemental", 7: "Ore/Stone", 8: "Meat",
            12: "Enchanting", 11: "Other", 1: "Parts"}
NODE_YIELD = {9: 1.5, 7: 2.2, 6: 1.0, 5: 1.0}  # classic yield per node, by Trade Goods subclass
TABLES = ["item", "price_realm", "price_region", "spell", "spell_reagent", "craft_output",
          "creature", "area", "drop", "kill_event", "loot_event", "node_area", "sync_log"]
COPPER = {"market", "minBO", "historical", "gap", "node value", "value"}
NAME = "COALESCE(i.name, 'item ' || p.item_id)"


def _fmt(col, v):
    if col in COPPER:
        return gold(v)
    if col.endswith("%"):
        return pct(v)
    if col == "region sale":
        return "-" if v is None else f"{v:.3f}"
    return num(v)


def _table(cols, rows):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(_fmt(c, r[c]) for c in cols) + " |" for r in rows]
    return out + ["", f"rows: {len(rows)}", ""]


def build(conn):
    q = lambda sql: [dict(r) for r in conn.execute(sql)]
    sources = q("""SELECT source, fetched_at, rows, note FROM sync_log s
                   WHERE rowid = (SELECT MAX(rowid) FROM sync_log WHERE source = s.source)
                   ORDER BY source""")
    counts = [{"table": t, "rows": conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]}
              for t in TABLES]

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
    # craft_output is empty until M2, so also drop obvious processed goods by name
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
                 GROUP BY w.item_id ORDER BY item""")
    return {"sources": sources, "counts": counts, "snapshot": snapshot, "movers": movers,
            "gather": gather, "flip": flip, "watch": watch}


COLUMNS = {
    "sources": ["source", "fetched_at", "rows", "note"],
    "counts": ["table", "rows"],
    "movers": ["item", "market", "historical", "change %"],
    "gather": ["item", "type", "market", "minBO", "region sale", "node value"],
    "flip": ["item", "market", "minBO", "gap", "gap %"],
    "watch": ["item", "reason"],
}


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
             "## FLIP", "", "realm items, market >= 1g, minBO <= 0.7 x market; top 25 by gap.", "",
             *_table(COLUMNS["flip"], data["flip"]),
             "## WATCH", "", "recipe outputs or drops with no realm price.", "",
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
            "flip": "market >= 10000 copper, minBO <= 0.7 x market, sorted by gap, cap 25",
            "watch": "recipe outputs / drops with no realm price",
        },
        "columns": COLUMNS,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({"_meta": meta, **data}, indent=1))
    print(f"wrote {md_path} and {json_path}: " + ", ".join(
        f"{k} {len(data[k])}" for k in ("snapshot", "movers", "gather", "flip", "watch")))
    return data
