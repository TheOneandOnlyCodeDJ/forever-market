import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fm import db, fmt, report  # noqa: E402


def _db(tmp_path, sources, prices=()):
    """sources: (name, kills, copper, {item: drops}); prices: (item, min_buyout, vendor_sell)."""
    conn = db.connect(tmp_path / "m.db")
    conn.execute("INSERT INTO loot_session VALUES ('c:1', 'c', 1, NULL, ?, 0, ?, 3600, 'now')",
                 (sum(s[1] for s in sources), sum(s[2] for s in sources)))
    for name, kills, copper, items in sources:
        conn.execute("INSERT INTO loot_source VALUES ('c:1', ?, ?, ?)", (name, kills, copper))
        conn.executemany("INSERT INTO loot_item_source VALUES ('c:1', ?, ?, ?)",
                         [(name, i, n) for i, n in items.items()])
        conn.executemany("INSERT INTO loot_item VALUES ('c:1', ?, ?, NULL, NULL, NULL)", items.items())
    for item, min_bo, vendor in prices:
        conn.execute("INSERT INTO price_realm (item_id, min_buyout) VALUES (?, ?)", (item, min_bo))
        conn.execute("INSERT INTO item (id, vendor_sell) VALUES (?, ?)", (item, vendor))
    return conn


def test_ev_maths(tmp_path):
    # 5 drops / 20 kills = 25%, valued 0.95 x 2000 = 1900c -> 475c/kill loot; 10000c coin / 20 kills -> 500c/kill.
    conn = _db(tmp_path, [("Wolf", 20, 10000, {1: 5})], [(1, 2000, 0)])
    (r,), _, _ = report.kill(conn)
    assert (r["rate"], r["loot/kill"], r["copper/kill"], r["total/kill"]) == (25.0, 475, 500, 975)
    assert fmt.coin(r["total/kill"]) == "9.75s"
    data = report.build(conn)
    assert data["farm"][0]["total/kill"] == 975 and data["farm_pace"][0]["copper/hour"] == 19500  # 1 hour


def test_unvalued_drops_reach_footer(tmp_path):
    conn = _db(tmp_path, [("Wolf", 20, 0, {1: 4, 2: 6})], [(1, 0, 100)])
    data = report.build(conn)
    assert data["kill"][0]["loot/kill"] == 20
    assert data["kill_totals"]["value source"] == {"buyout": 0, "vendor": 4, "none": 6}
    md = report.render(data, "t")
    assert md.count("value source: buyout 0%, vendor 40%, none 60% (10 drops)") == 2  # KILL and FARM


def test_confidence_boundary_and_low_sample(tmp_path):
    conn = _db(tmp_path, [("A", 49, 0, {}), ("B", 50, 0, {}), ("C", 9, 0, {})])
    data = report.build(conn)
    assert {r["source"]: r["confidence"] for r in data["farm"]} == {"A": "thin", "B": "ok"}
    assert data["farm_totals"]["low sample"] == 1
    farm = report.render(data, "t").split("## FARM")[1].split("## CRAFT")[0]
    assert "| C |" not in farm and "rows: 2" in farm
