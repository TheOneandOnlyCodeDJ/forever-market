import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from fm import __main__ as cli, blizzard, db, report  # noqa: E402


@pytest.fixture
def creds(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("BLIZZARD_CLIENT_ID=id\nBLIZZARD_CLIENT_SECRET=secret\nBLIZZARD_REGION=us\n")
    monkeypatch.setattr(blizzard, "ENV_PATH", env)
    monkeypatch.setattr(blizzard, "TOKEN_PATH", tmp_path / "cache" / "token.json")
    for k in ("BLIZZARD_CLIENT_ID", "BLIZZARD_CLIENT_SECRET", "BLIZZARD_REGION"):
        monkeypatch.delenv(k, raising=False)


def test_ruleset_index_parse():
    index = {"_links": {}, "rulesets": [{"id": 1, "name": "Normal"}, {"id": 2, "name": {"en_US": "Hardcore"}}]}
    assert blizzard.rulesets(index) == [(1, "Normal"), (2, "Hardcore")]
    assert blizzard.rulesets({}) == []


def test_house_index_trailing_slash():
    assert blizzard.house_path(3) == "/data/wow/ruleset/3/auctions/"
    assert blizzard.house_path(3, 111) == "/data/wow/ruleset/3/auctions/111"
    assert blizzard.house_path(3, 111, commodities=True) == "/data/wow/ruleset/3/auctions/111/commodities"
    index = {"auctions": [{"key": {"href": "x"}, "name": "Horde 1", "id": 116}, {"name": "broken"}]}
    assert blizzard.houses(index) == [(116, "Horde 1")]


def test_house_without_auctions_key(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    auctions, comm = blizzard.store_house(conn, 1, 112, "Horde 2", {"id": 112, "name": "Horde 2"}, None, "t")
    assert auctions == [] and comm == []
    assert tuple(conn.execute("SELECT faction, auctions, commodities FROM api_house").fetchone()) == ("Horde", 0, 0)


def test_commodity_unit_price():
    rows = blizzard.commodity_rows(116, [{"id": 9, "item": {"id": 2447}, "quantity": 20, "unit_price": 33,
                                          "time_left": "LONG"}], "t")
    assert rows == [(116, 2447, 20, 33, "t")]


def test_auction_upsert_replaces_stale_rows(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    old = {"auctions": [{"id": 1, "item": {"id": 2447}, "buyout": 100, "quantity": 1},
                        {"id": 2, "item": {"id": 2589}, "buyout": 50, "quantity": 2}]}
    new = {"auctions": [{"id": 3, "item": {"id": 2447}, "buyout": 90, "bid": 80, "quantity": 5, "time_left": "SHORT"}]}
    blizzard.store_house(conn, 1, 116, "Horde 1", old, [], "t1")
    blizzard.store_house(conn, 1, 116, "Horde 1", new, [], "t2")
    assert [tuple(r) for r in conn.execute("SELECT * FROM api_auction")] == [
        (116, 3, 2447, 5, 90, 80, None, "SHORT", "t2")]
    data = report.build(conn)
    assert data["api"][0]["api minBO"] == 18 and data["api"][0]["api qty"] == 5


def test_unresolved_item_counted_not_raised(tmp_path, creds, capsys):
    conn = db.connect(tmp_path / "m.db")
    conn.execute("INSERT INTO item (id, name) VALUES (2447, 'Peacebloom')")
    conn.execute("INSERT INTO price_realm (item_id, market_value) VALUES (2447, 20)")
    responses = {
        "/data/wow/ruleset/1": {"id": 1},
        "/data/wow/ruleset/1/auctions/": {"auctions": [{"id": 110, "name": "Alliance 1"},
                                                        {"id": 116, "name": "Horde 1"},
                                                        {"id": 121, "name": "Blackwater 1"}]},
        "/data/wow/ruleset/1/auctions/116": {"auctions": [{"id": 1, "item": {"id": 2447}, "buyout": 30, "quantity": 1},
                                                          {"id": 2, "item": {"id": 999999}, "buyout": 5, "quantity": 1}]},
        "/data/wow/ruleset/1/auctions/121": {"id": 121},
    }

    def fake_get(path, region=None):
        if path.endswith("/commodities"):
            raise blizzard.BlizzardError(404, b"not found")
        return responses[path]

    out = blizzard.sync(conn, get=fake_get)
    assert out == {"houses": 2, "auctions": 2, "commodities": 0, "ids": 2, "missing": 1}
    t = report.build(conn)
    assert t["api_totals"]["unresolved"] == 1 and t["api_totals"]["houses"] == ["Horde 1"]
    assert t["api"][0] == {"item": "Peacebloom", "api minBO": 30, "api qty": 1, "tsm market": 20,
                           "tsm minBO": None, "diff %": 50.0}


def test_token_cached_and_reused(creds):
    calls = []

    def stub(url, data=None, headers=None):
        calls.append(url)
        if url == blizzard.TOKEN_URL:
            assert headers["Authorization"].startswith("Basic ") and data == b"grant_type=client_credentials"
            return 200, json.dumps({"access_token": "tok", "expires_in": 86399}).encode()
        assert headers["Authorization"] == "Bearer tok" and headers["Accept-Encoding"] == "gzip"
        return 200, b'{"rulesets": []}'

    for _ in range(3):
        assert blizzard.get("/data/wow/ruleset/index", transport=stub) == {"rulesets": []}
    assert calls.count(blizzard.TOKEN_URL) == 1
    assert calls[1] == "https://us.api.blizzard.com/data/wow/ruleset/index?namespace=dynamic-forever-us"
    # within 120 s of expiry the cached token is refreshed
    assert blizzard.token(stub, now=lambda: blizzard.time.time() + 86399 - 100) == "tok"
    assert calls.count(blizzard.TOKEN_URL) == 2


def test_http_error_raises_blizzard_error(creds):
    stub = lambda url, data=None, headers=None: (200, b'{"access_token": "t", "expires_in": 999}') \
        if url == blizzard.TOKEN_URL else (404, b'{"code": 404}')
    with pytest.raises(blizzard.BlizzardError, match="HTTP 404"):
        blizzard.get("/data/wow/item/1", transport=stub)


def test_missing_credentials_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(blizzard, "ENV_PATH", tmp_path / "absent.env")
    for k in ("BLIZZARD_CLIENT_ID", "BLIZZARD_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    for argv in (["api", "probe"], ["sync", "api", "--houses", "horde"]):
        assert cli.main(argv) == 2
        out = capsys.readouterr().out
        assert len(out.strip().splitlines()) == 1 and "BLIZZARD_CLIENT_ID" in out


def test_api_section_empty_db(tmp_path):
    lines = report._api_lines(report.build(db.connect(tmp_path / "e.db")))
    assert lines == ["no api data yet", "", "rows: 0", ""]
