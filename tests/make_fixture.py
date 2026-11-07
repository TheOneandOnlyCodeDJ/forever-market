"""Rebuild tests/fixtures/market_fixture.db offline: `python3 tests/make_fixture.py`."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fm import db, sync_prices  # noqa: E402

OUT = HERE / "fixtures" / "market_fixture.db"
# Copied from wago Item + ItemSparse build 1.60.1.70790 on 2026-11-07.
ITEMS = [
    (1725, "Large Knapsack", 1, 35, 0, 1, 0, 0, 1, 5000, "forever"),
    (2318, "Light Leather", 1, 10, 0, 7, 6, 0, 20, 15, "forever"),
    (2447, "Peacebloom", 1, 5, 0, 7, 9, 0, 20, 10, "forever"),
    (2458, "Elixir of Minor Fortitude", 1, 12, 2, 0, 2, 0, 20, 15, "forever"),
    (2589, "Linen Cloth", 1, 5, 0, 7, 5, 0, 20, 13, "forever"),
    (2770, "Copper Ore", 1, 10, 0, 7, 7, 0, 20, 5, "forever"),
    (4306, "Silk Cloth", 1, 30, 0, 7, 5, 0, 20, 150, "forever"),
    (5964, "Barbaric Shoulders", 2, 35, 30, 4, 2, 2, 1, 2609, "forever"),
    (9294, "Recipe: Wildvine Potion", 2, 45, 0, 9, 6, 0, 1, 2000, "forever"),
    (14047, "Runecloth", 1, 50, 0, 7, 5, 0, 20, 400, "forever"),
]


def main():
    OUT.unlink(missing_ok=True)
    conn = db.connect(OUT)
    for source, path in sync_prices.FIXTURES.items():
        sync_prices.ingest(conn, source, path.read_text())
    conn.executemany("INSERT INTO item VALUES (?,?,?,?,?,?,?,?,?,?,?)", ITEMS)
    # Alchemy "Elixir of Minor Fortitude" (spell 2334); its output has no fixture price -> WATCH row.
    conn.execute("INSERT INTO craft_output VALUES (2334, 2458, 1)")
    conn.execute("UPDATE sync_log SET fetched_at = '2026-11-07 21:00:00'")  # stable fixture bytes
    conn.commit()
    conn.close()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
