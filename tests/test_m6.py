import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fm import db, report  # noqa: E402


def _db(tmp_path, items=(), source=None):
    """items: (id, bonding, quality, vendor_sell, min_buyout, sale_rate); source: (kills, {item: drops})."""
    conn = db.connect(tmp_path / "m.db")
    for i, bond, q, vendor, min_bo, rate in items:
        conn.execute("INSERT INTO item (id, name, bonding, quality, vendor_sell) VALUES (?, ?, ?, ?, ?)",
                     (i, f"I{i}", bond, q, vendor))
        if min_bo is not None:
            conn.execute("INSERT INTO price_realm (item_id, min_buyout) VALUES (?, ?)", (i, min_bo))
        if rate is not None:
            conn.execute("INSERT INTO price_region (item_id, sale_rate) VALUES (?, ?)", (i, rate))
    if source:
        kills, drops = source
        conn.execute("INSERT INTO loot_session VALUES ('c:1', 'c', 1, NULL, ?, 0, 0, 3600, 'now')", (kills,))
        conn.execute("INSERT INTO loot_source VALUES ('c:1', 'Boar', ?, 0)", (kills,))
        conn.executemany("INSERT INTO loot_item_source VALUES ('c:1', 'Boar', ?, ?)", drops.items())
        conn.executemany("INSERT INTO loot_item VALUES ('c:1', ?, ?, NULL, NULL, NULL)", drops.items())
    return conn


def test_value_of(tmp_path):
    conn = _db(tmp_path, [(1, 0, 1, 100, 200, None), (2, 0, 1, 500, 200, None), (3, 0, 1, 0, 0, None)])
    assert report.value_of(conn, 1) == (190, "buyout")
    assert report.value_of(conn, 2) == (500, "vendor")
    assert report.value_of(conn, 3) == (0, "none")
    assert report.value_of(conn, 99) == (0, "none")


def _flags(conn):
    return {r["item"]: r["flag"] for r in report.build(conn)["boe"]}


def test_boe_flags_and_bonding(tmp_path):
    conn = _db(tmp_path, [(1, 2, 2, 25000, None, None),     # 2.5g vendor, no listing -> scarce
                          (2, 2, 3, 100, 10000, 0.31),       # demand
                          (3, 2, 2, 100, 10000, None),       # listed, no sale rate -> thin
                          (4, 1, 4, 100, 99999, 0.9),        # bind on pickup -> never shown
                          (5, 2, 2, 0, None, None)],         # source none -> dropped
               (10, {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}))
    assert _flags(conn) == {"I1": "scarce", "I2": "demand", "I3": "thin"}
    assert report.build(conn)["boe_totals"] == {"candidates": 4, "dropped none": 1}
    md = report.render(report.build(conn), "t")
    assert md.index("## FARM") < md.index("## BOE") < md.index("## CRAFT")
    assert "| I4 |" not in md.split("## BOE")[1].split("## CRAFT")[0]


def test_kill_uses_vendor_floor(tmp_path):
    conn = _db(tmp_path, [(1, 0, 1, 100, None, None)], (1, {1: 1}))
    assert report._loot(conn, "c:1", "Boar") == [("I1", 100.0, 1, 100, "vendor")]  # 1 kill: 100c/kill
    conn = _db(tmp_path / "b", [(1, 0, 1, 100, None, None)], (5, {1: 5}))  # KILL lists kills >= 5 only
    (r,), _, _ = report.kill(conn)
    assert r["loot/kill"] == 100
