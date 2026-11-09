"""Hourly snapshots (price_history) and the price indices derived from them (index_history)."""
import statistics
from datetime import datetime, timezone

CATEGORIES = {7: "Trade goods", 0: "Consumables", 4: "Armour", 2: "Weapons", 9: "Recipes"}
ALL = "Forever 100"
MIN_ITEMS = 20
TSM_HOUSE = 0  # the TSM realm feed has no house id; NULL would defeat the primary key


def hour(now=None):
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:00:00Z")


def append(conn, at, source, region, house_id, rows):
    """rows: (item_id, min_buyout, market, listings, qty). Replaces this series' snapshot for the hour."""
    conn.execute("DELETE FROM price_history WHERE at = ? AND source = ? AND region = ? AND house_id = ?",
                 (at, source, region, house_id))
    conn.executemany("INSERT INTO price_history VALUES (?,?,?,?,?,?,?,?,?)",
                     [(at, source, region, house_id, *r) for r in rows])
    conn.commit()
    return len(rows)


def api_rows(auctions, commodities):
    """blizzard.auction_rows + commodity_rows tuples -> per item (id, cheapest unit, None, listings, qty)."""
    units = [(a[2], a[4] // a[3], a[3]) for a in auctions if a[2] is not None and a[3] and a[4]]
    units += [(c[1], c[3], c[2]) for c in commodities if c[1] is not None and c[2] and c[3]]
    agg = {}
    for item, unit, qty in units:
        cur = agg.setdefault(item, [unit, 0, 0])
        cur[:] = min(cur[0], unit), cur[1] + 1, cur[2] + qty
    return [(item, lo, None, n, qty) for item, (lo, n, qty) in sorted(agg.items())]


def snapshot_tsm(conn, region="us", at=None):
    """price_realm as it stands -> one tsm snapshot, then the indices for that hour."""
    at = at or hour()
    n = append(conn, at, "tsm", region, TSM_HOUSE, conn.execute(
        "SELECT item_id, NULLIF(min_buyout, 0), NULLIF(market_value, 0), NULL, NULL FROM price_realm").fetchall())
    return n, write_indices(conn, at, region)


def write_indices(conn, at, region="us"):
    """100 x median(market now / market at the first tsm snapshot) per item class -> ({category: value}, skipped)."""
    key = ("tsm", region, TSM_HOUSE)
    first = conn.execute("SELECT MIN(at) FROM price_history WHERE source = ? AND region = ? AND house_id = ?",
                         key).fetchone()[0]
    ratios = {}
    for class_id, ratio in conn.execute(
            """SELECT i.class_id, 1.0 * n.market / f.market FROM price_history n
               JOIN price_history f ON f.source = n.source AND f.region = n.region AND f.house_id = n.house_id
                                   AND f.item_id = n.item_id AND f.at = ?
               LEFT JOIN item i ON i.id = n.item_id
               WHERE n.at = ? AND n.source = ? AND n.region = ? AND n.house_id = ? AND n.market > 0 AND f.market > 0""",
            (first, at, *key)):
        ratios.setdefault(CATEGORIES.get(class_id, "Other"), []).append(ratio)
        ratios.setdefault(ALL, []).append(ratio)
    written = {c: 100 * statistics.median(r) for c, r in ratios.items() if len(r) >= MIN_ITEMS}
    skipped = {c: len(ratios.get(c, [])) for c in (*CATEGORIES.values(), "Other", ALL) if c not in written}
    conn.execute("DELETE FROM index_history WHERE at = ?", (at,))
    conn.executemany("INSERT INTO index_history VALUES (?,?,?)", [(at, c, v) for c, v in written.items()])
    conn.commit()
    return written, skipped
