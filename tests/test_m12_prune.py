import datetime as dt
import sqlite3

from fm import db, prune


def _db(tmp_path):
    conn = db.connect(tmp_path / "p.db")
    return conn


def _insert(conn, at, item_id=1, source="api", region="us", house_id=113):
    conn.execute(
        "INSERT OR REPLACE INTO price_history (at, source, region, house_id, item_id, min_buyout, market, listings, qty)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (at, source, region, house_id, item_id, 100, 100, 1, 1),
    )


def test_prune_keeps_three_buckets(tmp_path):
    conn = _db(tmp_path)
    now = dt.datetime(2026, 11, 10, 12, 0, tzinfo=dt.timezone.utc)

    def iso(days_ago, hour=0):
        return (now - dt.timedelta(days=days_ago, hours=hour)).strftime("%Y-%m-%dT%H:00:00Z")

    _insert(conn, iso(0), item_id=1)                 # recent: hourly, kept
    _insert(conn, iso(0, 1), item_id=2)              # recent: hourly, kept
    _insert(conn, iso(10), item_id=3)                # daily bucket
    _insert(conn, iso(10, 6), item_id=3)             # same day, earlier: deleted, later survives
    _insert(conn, iso(100), item_id=4)               # past 90 days: deleted
    conn.commit()

    stats = prune.run(conn, now=now)
    assert stats["total"] == 5
    assert stats["hourly"] == 2
    assert stats["daily"] == 1
    assert stats["deleted"] == 2
    left = conn.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
    assert left == 3


def test_prune_dry_run_deletes_nothing(tmp_path):
    conn = _db(tmp_path)
    now = dt.datetime(2026, 11, 10, 12, 0, tzinfo=dt.timezone.utc)
    _insert(conn, "2026-01-01T00:00:00Z")
    conn.commit()
    stats = prune.run(conn, now=now, dry_run=True)
    assert stats["deleted"] == 1
    assert conn.execute("SELECT COUNT(*) FROM price_history").fetchone()[0] == 1


def test_prune_keeps_last_row_of_each_day(tmp_path):
    conn = _db(tmp_path)
    now = dt.datetime(2026, 11, 10, 12, 0, tzinfo=dt.timezone.utc)
    for hour in (2, 8, 14, 20):
        _insert(conn, f"2026-10-20T{hour:02d}:00:00Z")
    conn.commit()
    stats = prune.run(conn, now=now)
    assert stats["daily"] == 1
    survivor = conn.execute("SELECT at FROM price_history").fetchone()[0]
    assert survivor == "2026-10-20T20:00:00Z"
