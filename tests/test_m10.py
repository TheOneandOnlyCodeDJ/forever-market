import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from fm import blizzard, db, export_addon, history, lua_table  # noqa: E402

H1, H2 = "2026-11-10T05:00:00Z", "2026-11-10T06:00:00Z"
SV = "WTF/Account/A#1/SavedVariables"


@pytest.fixture
def conn(tmp_path, monkeypatch):
    for k in ("FM_FORCE_GAME_RUNNING", "FM_FORCE_GAME_CLOSED", "FM_API_HOUSE"):
        monkeypatch.delenv(k, raising=False)
    (tmp_path / SV).mkdir(parents=True)
    return db.connect(tmp_path / "m.db")


def _prices(conn, n, market, class_id=7, start=1):
    conn.executemany("INSERT OR REPLACE INTO item (id, name, class_id) VALUES (?, ?, ?)",
                     [(i, f"item {i}", class_id) for i in range(start, start + n)])
    conn.executemany("INSERT OR REPLACE INTO price_realm (item_id, market_value, min_buyout) VALUES (?, ?, ?)",
                     [(i, market, market) for i in range(start, start + n)])


def test_history_append_idempotent_within_hour(conn):
    _prices(conn, 3, 100)
    assert conn.execute("SELECT region FROM api_house").fetchall() == []  # column exists
    for _ in range(2):
        history.snapshot_tsm(conn, at=H1)
        auctions = blizzard.auction_rows(113, {"auctions": [
            {"id": 1, "item": {"id": 2}, "buyout": 500, "quantity": 5},
            {"id": 2, "item": {"id": 2}, "buyout": 90, "quantity": 1}]}, "t")
        history.append(conn, H1, "api", "us", 113, history.api_rows(auctions, [(113, 9, 4, 7, "t")]))
    assert conn.execute("SELECT COUNT(*) FROM price_history").fetchone()[0] == 5
    assert [tuple(r) for r in conn.execute(
        "SELECT item_id, min_buyout, market, listings, qty FROM price_history WHERE source = 'api' ORDER BY 1")] == [
        (2, 90, None, 2, 6), (9, 7, None, 1, 4)]


def test_index_maths_and_19_item_floor(conn):
    _prices(conn, 20, 100, class_id=7)
    _prices(conn, 19, 100, class_id=0, start=100)
    history.snapshot_tsm(conn, at=H1)
    _prices(conn, 20, 150, class_id=7)
    _prices(conn, 19, 50, class_id=0, start=100)
    _, (written, skipped) = history.snapshot_tsm(conn, at=H2)
    assert written == {"Trade goods": 150.0, "Forever 100": 150.0}  # 20 at 1.5, 19 at 0.5: median 1.5
    assert skipped["Consumables"] == 19
    assert dict(conn.execute("SELECT category, index_value FROM index_history WHERE at = ?", (H2,))) == written
    assert dict(conn.execute("SELECT category, index_value FROM index_history WHERE at = ?", (H1,)))["Trade goods"] == 100.0


def test_export_round_trip_cap_window(conn, tmp_path):
    conn.execute("INSERT INTO item (id, name, quality, item_level, vendor_sell) VALUES (1, 'Cerulean \"Dye\"', 1, 25, 7500)")
    blizzard.store_house(conn, 1, 113, "Horde", {"auctions": [{"id": 1, "item": {"id": 1}, "buyout": 250, "quantity": 1}]}, [], "t")
    hours = [f"2026-11-{d:02d}T{h:02d}:00:00Z" for d in range(1, 9) for h in range(24)]  # 192 hours
    for at in hours:
        history.append(conn, at, "tsm", "us", 0, [(1, 300, 400, None, None)])
        history.append(conn, at, "api", "us", 113, [(1, 250, None, 3, 9)])
    history.append(conn, hours[-1], "api", "eu", 113, [(1, 200, None, 1, 1)])
    conn.execute("INSERT INTO index_history VALUES (?, 'Forever 100', 84.2)", (hours[-1],))
    conn.executemany("INSERT INTO loot_item_source VALUES ('s', 'mob', ?, 1)", [(i,) for i in range(2, 2100)])
    assert export_addon.run(conn, tmp_path) == 0
    data_file = tmp_path / "Interface/AddOns/ForeverMarketUI/Data.lua"
    assert data_file.exists()  # written straight into the addon folder, no SavedVariables, no pending
    out = lua_table.parse(data_file.read_text())["ForeverMarketData"]
    assert (out["house"], out["region"]) == (113, "us")
    assert out["indices"] == {"Forever 100": [{"t": 1794178800, "v": 84.2}]}
    # coverage is capped by bytes now, not by item count: everything priced fits, and a
    # low byte cap trims the cheapest items instead of truncating the list
    assert "i:1" in out["items"] and out["items"]["i:1"]["res"] == "h"
    assert len(out["items"]) == 2099
    item = out["items"]["i:1"]
    assert (item["n"], item["q"], item["il"], item["vendor"]) == ('Cerulean "Dye"', 1, 25, 7500)
    assert "regions" not in item  # single region: no per-region block any more
    assert out["generated_ts"] and out["next_update"] == out["generated_ts"] + 3600
    assert len(item["series"]) == 168
    # both sources survive in one point so the addon can draw two cheapest lines
    assert item["series"][-1] == {"t": 1794178800, "typical": 400, "tsmcheap": 300,
                                   "cheapest": 250, "qty": 9, "auctions": 3}
    assert out["items"]["i:2"] == {"res": "h", "series": {}}  # measured drop, no name or price known: nothing invented


def test_export_is_atomic_and_needs_no_closed_game(conn, tmp_path, capsys):
    # the client never touches addon Lua files, so a running game is irrelevant now
    assert export_addon.run(conn, tmp_path) == 0
    folder = tmp_path / "Interface/AddOns/ForeverMarketUI"
    assert (folder / "Data.lua").exists()
    assert not (folder / "Data.lua.tmp").exists()  # temp file is renamed, not left behind
    assert "/reload picks it up" in capsys.readouterr().out
