import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fm import db, import_loot, lua_table, report  # noqa: E402

CLIENT = ROOT / "tests" / "fixtures" / "client"
ALPHA = next(CLIENT.glob("WTF/Account/*/*/Alpha-Test/SavedVariables/LootTrackerForever.lua"))


def _dump(v):
    """Minimal Lua writer, only to round-trip the parser."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(v, list):
        return "{\n" + "".join(f"{_dump(x)},\n" for x in v) + "}"
    return "{\n" + "".join(f"[{_dump(k)}] = {_dump(x)},\n" for k, x in v.items()) + "}"


def test_parser_round_trip():
    text = ALPHA.read_bytes().decode()
    assert "\r\n" in text
    data = lua_table.parse(text)
    s = data["LootTrackerForeverData"]["session"]
    assert s["note"] == 'say "hi"\\path\nline2'
    assert s["items"]["769"]["link"] == "|cffffffff|Hitem:769::::::::5:1482:::::::::|h[Chunk of Boar Meat]|h|r"
    assert s["sources"]["Mottled Boar"]["items"] == {"769": 2, "4865": 6}
    assert (s["elapsed"], s["paused"], s["feed"]) == (600.5, False, [{"key": "769", "count": 1}])
    assert lua_table.parse("".join(f"{k} = {_dump(v)}\n" for k, v in data.items())) == data
    bare = lua_table.parse(next(CLIENT.glob("WTF/Account/*/*/Beta-Test/SavedVariables/*.lua")).read_text())
    assert bare["LootTrackerForeverData"]["session"]["items"][10940]["name"] == "Strange Dust"
    assert bare["LootTrackerForeverData"]["session"]["ratio"] == -150.0


def _imported(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    import_loot.run(conn, CLIENT)
    return conn


def _counts(conn):
    return [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("loot_session", "loot_source", "loot_item_source", "loot_item")]


def test_drop_rate_8_kills_2_drops(tmp_path):
    rows, measured, footer = report.kill(_imported(tmp_path))
    assert [(r["source"], r["kills"], r["copper/kill"], r["best item"], r["rate"], r["sample"]) for r in rows] == \
        [("Fixture Wolf", 20, 0, "Light Leather", 20.0, 20), ("Mottled Boar", 8, 15, "Ruined Pelt", 75.0, 8)]
    rates = {r["item"]: r["rate"] for r in _imported(tmp_path).execute(report.RATES)}
    assert rates["Chunk of Boar Meat"] == 25.0
    assert measured == [{"item": "Light Leather", "source": "Fixture Wolf", "kills": 20, "drops": 4, "rate %": 20.0}]
    assert footer == {"sessions": 2, "characters": 2, "kills": 28}


def test_reimport_is_idempotent(tmp_path):
    conn = _imported(tmp_path)
    first = _counts(conn)
    import_loot.run(conn, CLIENT)
    assert _counts(conn) == first == [2, 4, 4, 4]


def test_kill_empty_db(tmp_path):
    lines = report._kill_lines(report.build(db.connect(tmp_path / "m.db")))
    assert lines == ["no loot data yet", "", "rows: 0", ""]
