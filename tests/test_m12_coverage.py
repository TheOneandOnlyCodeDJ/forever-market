import sqlite3

from fm import db, export_addon


def _seed(conn, n=5, points=4):
    conn.execute("INSERT INTO api_house (house_id, ruleset_id, name, faction, auctions, commodities, fetched_at, region)"
                 " VALUES (113, 1, 'Horde Auction House', 'Horde', 0, 0, 'x', 'us')")
    for i in range(1, n + 1):
        conn.execute("INSERT INTO item (id, name, quality, item_level) VALUES (?, ?, 2, 20)", (i, f"Item {i}"))
        for h in range(points):
            conn.execute(
                "INSERT INTO price_history (at, source, region, house_id, item_id, min_buyout, market, listings, qty)"
                " VALUES (?, 'api', 'us', 113, ?, ?, ?, 1, 1)",
                (f"2026-11-0{h + 1}T00:00:00Z", i, 1000 * (n + 1 - i), 1000 * (n + 1 - i)))
    conn.commit()


def test_tiering_marks_hourly_and_daily(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "c.db")
    _seed(conn)
    monkeypatch.setattr(export_addon, "TOP_API", 2)
    data, stats = export_addon.build(conn)
    assert stats["tier1"] == 2 and stats["tier2"] == 3
    res = {k: v.get("res") for k, v in data["items"].items()}
    # with only a handful of hours of history every series stays hourly, including tier 2:
    # daily downsampling would flatten a two point series into a straight line
    assert res["i:1"] == "h" and res["i:2"] == "h" and res["i:5"] == "h"


def test_tier2_goes_daily_once_history_is_long(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "c.db")
    _seed(conn)
    # a week of hourly snapshots is more than the addon plots, so tier 2 downsamples
    for h in range(200):
        conn.execute("INSERT INTO price_history (at, source, region, house_id, item_id, min_buyout, market, listings, qty)"
                     " VALUES (?, 'api', 'us', 113, 1, 1000, 1000, 1, 1)",
                     (f"2026-10-{1 + h // 24:02d}T{h % 24:02d}:00:00Z",))
    conn.commit()
    monkeypatch.setattr(export_addon, "TOP_API", 2)
    data, stats = export_addon.build(conn)
    assert data["items"]["i:3"]["res"] == "d"


def test_byte_cap_skips_cheapest_first(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "c.db")
    _seed(conn, n=8)
    monkeypatch.setattr(export_addon, "TOP_API", 1)
    monkeypatch.setattr(export_addon, "MAX_BYTES", 1_500)
    data, stats = export_addon.build(conn)
    assert stats["skipped"] > 0
    # the most expensive item always survives, the cheapest are the ones dropped
    assert "i:1" in data["items"]
    assert "i:8" not in data["items"] or stats["skipped"] == 0


def test_daily_series_keeps_last_row_of_the_day(tmp_path):
    conn = db.connect(tmp_path / "c.db")
    conn.execute("INSERT INTO api_house (house_id, ruleset_id, name, faction, auctions, commodities, fetched_at, region)"
                 " VALUES (113, 1, 'Horde', 'Horde', 0, 0, 'x', 'us')")
    conn.execute("INSERT INTO item (id, name) VALUES (1, 'Item 1')")
    for at, lo in (("2026-11-01T01:00:00Z", 100), ("2026-11-01T09:00:00Z", 200)):
        conn.execute("INSERT INTO price_history (at, source, region, house_id, item_id, min_buyout, market, listings, qty)"
                     " VALUES (?, 'api', 'us', 113, 1, ?, ?, 1, 1)", (at, lo, lo))
    conn.commit()
    series = export_addon._series(conn, [1], 113, "us", daily=True)
    points = series[1]
    assert len(points) == 1  # one row for the day, the later one
    assert list(points.values())[0]["cheapest"] == 200
