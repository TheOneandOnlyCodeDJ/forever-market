import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fm import db, report, sync_recipes  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def _csv(name):
    return sync_recipes.rows((FIXTURES / f"{name}.csv").read_text())


def test_spell_listed_twice_keeps_lowest_rank():
    assert sync_recipes.abilities(_csv("SkillLineAbility")) == {2330: ("Alchemy", 50, 7)}


def test_num_result_clamped():
    assert sync_recipes.outputs(_csv("SpellEffect")) == [(2330, 118, 1), (2657, 2840, 1), (2665, 2512, 200)]


def _craft_db(tmp_path, min_buyout):
    conn = db.connect(tmp_path / "m.db")
    conn.execute("INSERT INTO item (id, name) VALUES (10, 'Mat'), (20, 'Thing')")
    conn.execute("INSERT INTO spell VALUES (1, 'Make Thing', 'Tailoring', 50, NULL)")
    conn.execute("INSERT INTO spell_reagent VALUES (1, 10, 2)")
    conn.execute("INSERT INTO craft_output VALUES (1, 20, 1)")
    conn.execute("INSERT INTO price_realm VALUES (10, 50, 50, NULL, NULL, NULL)")
    conn.execute("INSERT INTO price_realm VALUES (20, 200, ?, NULL, NULL, NULL)", (min_buyout,))
    return conn


def test_craft_margin_maths(tmp_path):
    rows, skipped = report.craft(_craft_db(tmp_path, 150))
    r = rows[0]
    assert (r["item"], r["profession"], r["cost"], r["sell"], r["profit"], r["margin %"], r["listed"]) == \
        ("Thing", "Tailoring", 100, 190, 90, 90.0, "yes")
    assert skipped == {"priced": 1, "unpriced mats": 0, "no realm price": 0}


def test_craft_hidden_and_region_fallback(tmp_path):
    conn = _craft_db(tmp_path, 0)
    conn.execute("DELETE FROM price_realm WHERE item_id = 10")
    conn.execute("INSERT INTO price_region (item_id, market_value) VALUES (10, 50)")
    r = report.craft(conn)[0][0]
    assert (r["item"], r["profession"], r["listed"], r["profit"]) == ("HIDDEN Thing", "Tailoring*", "no", 90)


def test_craft_skips_unpriced_mats(tmp_path):
    conn = _craft_db(tmp_path, 150)
    conn.execute("DELETE FROM price_realm WHERE item_id = 10")
    assert report.craft(conn) == ([], {"priced": 0, "unpriced mats": 1, "no realm price": 0})


def test_processed_goods_not_in_gather():
    conn = sqlite3.connect(FIXTURES / "market_fixture.db")
    conn.row_factory = sqlite3.Row
    data = report.build(conn)
    gather = {r["item"] for r in data["gather"]}
    assert "Copper Ore" in gather
    assert not gather & {"Copper Bar", "Bolt of Linen Cloth"}
    assert [r["item"] for r in data["craft"]] == ["Bolt of Linen Cloth", "Copper Bar"]
