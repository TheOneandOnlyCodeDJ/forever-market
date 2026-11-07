import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fm import db, fmt, report  # noqa: E402


def _db(tmp_path, sources, prices=()):
    """sources: (name, kills, copper, {item: drops}); prices: (table, item, market_value)."""
    conn = db.connect(tmp_path / "m.db")
    conn.execute("INSERT INTO loot_session VALUES ('c:1', 'c', 1, NULL, ?, 0, ?, 3600, 'now')",
                 (sum(s[1] for s in sources), sum(s[2] for s in sources)))
    for name, kills, copper, items in sources:
        conn.execute("INSERT INTO loot_source VALUES ('c:1', ?, ?, ?)", (name, kills, copper))
        conn.executemany("INSERT INTO loot_item_source VALUES ('c:1', ?, ?, ?)",
                         [(name, i, n) for i, n in items.items()])
        conn.executemany("INSERT INTO loot_item VALUES ('c:1', ?, ?, NULL, NULL, NULL)", items.items())
    for table, item, mv in prices:
        conn.execute(f"INSERT INTO {table} (item_id, market_value) VALUES (?, ?)", (item, mv))
    return conn


def test_ev_maths(tmp_path):
    # Brief inputs (25% at 100c) give 25c, not its stated 500c; kept its outputs with consistent inputs:
    # 5 drops / 20 kills = 25% at 2000c -> 500c/kill loot; 10000c coin / 20 kills -> 500c/kill.
    conn = _db(tmp_path, [("Wolf", 20, 10000, {1: 5})], [("price_region", 1, 2000)])
    assert report.price_of(conn, 1) == (2000, "region")
    assert report.price_of(conn, 2) == (None, "none")
    (r,), _, _ = report.kill(conn)
    assert (r["rate"], r["loot/kill"], r["copper/kill"], r["total/kill"]) == (25.0, 500, 500, 1000)
    assert fmt.coin(r["total/kill"]) == "10.00s"
    data = report.build(conn)
    assert data["farm"][0]["total/kill"] == 1000 and data["farm_pace"][0]["copper/hour"] == 20000  # 1 hour


def test_realm_price_wins(tmp_path):
    conn = _db(tmp_path, [], [("price_realm", 1, 300), ("price_region", 1, 2000), ("price_realm", 2, 0)])
    assert report.price_of(conn, 1) == (300, "realm")
    assert report.price_of(conn, 2) == (None, "none")  # TSM 0 = no data


def test_unpriced_drops_reach_footer(tmp_path):
    conn = _db(tmp_path, [("Wolf", 20, 0, {1: 4, 2: 6})], [("price_realm", 1, 100)])
    data = report.build(conn)
    assert data["kill"][0]["loot/kill"] == 20
    assert data["kill_totals"]["unpriced drops"] == 6
    assert data["farm_totals"]["price coverage %"] == 40.0
    md = report.render(data, "t")
    assert "drops with no price (counted as 0): 6" in md and "price coverage: 40.0% (4/10 drops priced)" in md


def test_confidence_boundary_and_low_sample(tmp_path):
    conn = _db(tmp_path, [("A", 49, 0, {}), ("B", 50, 0, {}), ("C", 9, 0, {})])
    data = report.build(conn)
    assert {r["source"]: r["confidence"] for r in data["farm"]} == {"A": "thin", "B": "ok"}
    assert data["farm_totals"]["low sample"] == 1
    farm = report.render(data, "t").split("## FARM")[1].split("## CRAFT")[0]
    assert "| C |" not in farm and "rows: 2" in farm
