import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fm import blizzard, db, report, web  # noqa: E402


def _house(conn, hid, auctions):
    """auctions: [(item_id, buyout, quantity)]"""
    blizzard.store_house(conn, 1, hid, "Horde Auction House",
                         {"auctions": [{"id": hid * 1000 + n, "item": {"id": i}, "buyout": b, "quantity": q}
                                       for n, (i, b, q) in enumerate(auctions)]}, [], "t")


def test_score_maths():
    # 100 vs 101 exact (1 copper), 200 vs 100 diff 1.0, 50 vs 100 diff 0.5; zero/None pairs ignored
    assert blizzard.score([(100, 101), (200, 100), (50, 100), (0, 5), (5, None)]) == (3, 1, 0.5)
    assert blizzard.score([]) == (0, 0, None)


def test_match_ranks_and_skips_empty_house(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    conn.executemany("INSERT INTO price_realm (item_id, min_buyout) VALUES (?, ?)", [(1, 100), (2, 200)])
    _house(conn, 113, [(1, 100, 1), (2, 400, 2)])          # unit 100 exact, 200 exact
    _house(conn, 114, [(1, 150, 1), (2, 200, 1), (2, 900, 1)])  # 150 off, 200 exact
    _house(conn, 115, [])
    rows = blizzard.match(conn)
    assert [r[:4] for r in rows] == [(113, 2, 2, 0.0), (114, 2, 1, 0.25)]
    assert [r[0] for r in conn.execute("SELECT house_id FROM api_house_match")] == [113, 114]


def test_single_house_selection_order(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    _house(conn, 113, [(1, 10, 1)])
    _house(conn, 114, [(1, 10, 1), (2, 10, 1)])
    _house(conn, 115, [])
    assert report.pick_house(conn, {}) == (114, "most auctions")
    conn.executemany("INSERT INTO api_house_match VALUES (?,?,?,?,?)",
                     [(114, 49, 49, 0.0, "t"), (113, 60, 15, 0.3, "t"), (120, 80, 16, 0.2, "t")])
    assert report.pick_house(conn, {}) == (113, "api_house_match")  # 114 below common 50; 25% beats 20%
    assert report.pick_house(conn, {"FM_API_HOUSE": "120"}) == (120, "FM_API_HOUSE")


def test_api_listings_column_single_house(tmp_path, monkeypatch):
    monkeypatch.delenv("FM_API_HOUSE", raising=False)
    conn = db.connect(tmp_path / "m.db")
    _house(conn, 113, [(1, 10, 1), (1, 30, 2)])
    _house(conn, 114, [(1, 5, 1), (1, 5, 1), (1, 5, 1)])
    data = report.build(conn)
    assert report.COLUMNS["api"][2:5] == ["api qty", "api listings", "tsm market"]
    assert data["api"][0]["api listings"] == 3 and data["api"][0]["api qty"] == 3  # 114 only, never summed
    lines = report._api_lines(data)
    assert lines[0].startswith("official Blizzard API, house 114 (Horde Auction House")
    assert "single house only: the five Horde houses are separate markets and are never summed" in lines[-2]
    assert "api listings" in web.build_html(data)


def test_probe_name_fallback(capsys):
    payloads = {"/data/wow/ruleset/index": {"rulesets": [{"key": {"href": "x"}, "id": 1}, {"id": 2, "name": "Hardcore"}]},
                "/data/wow/ruleset/1": {"id": 1},
                "/data/wow/ruleset/1/auctions/": {"auctions": [{"id": 113, "name": "Horde Auction House"}]}}
    blizzard.probe(get=lambda path, region=None: payloads[path])
    out = capsys.readouterr().out.splitlines()
    assert out[:3] == ["ruleset 1: -", "ruleset 2: Hardcore", "ruleset 1 detail: name=- status=None auctions=None"]
