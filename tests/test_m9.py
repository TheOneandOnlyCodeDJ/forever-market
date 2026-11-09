import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from fm import blizzard, db, export_tsm, lua_table, paths  # noqa: E402

PATCH = ROOT / "addon/tsm-patches/API.lua.patch"
LIVE_API = paths.CLIENT_DIR / "Interface/AddOns/TradeSkillMaster/App/API.lua"


@pytest.fixture
def client(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    blizzard.store_house(conn, 1, 113, "Horde", {"auctions": [
        {"id": 1, "item": {"id": 2}, "buyout": 500, "quantity": 5},
        {"id": 2, "item": {"id": 2}, "buyout": 90, "quantity": 1},
        {"id": 3, "item": {"id": 7}, "buyout": 300, "quantity": 1}]}, [], "2026-11-09 00:00:00")
    conn.executemany("INSERT INTO price_realm (item_id, market_value, min_buyout) VALUES (?, ?, ?)",
                     [(2, 120, 100), (9, 50, 40)])  # 9 has no api rows
    return conn, tmp_path


def test_export_round_trips(client):
    conn, root = client
    assert export_tsm.run(conn, root) == 0
    target = root / "Interface/AddOns/ForeverMarketBridge/Data.lua"
    assert target.exists()  # addon folder, not SavedVariables
    out = lua_table.parse(target.read_text())
    assert out["ForeverMarketPrice"] == {
        "i:2": {"minbo": 90, "qty": 6, "listings": 2, "market": 120, "value": 95, "at": "2026-11-09T00:00:00Z"},
        "i:7": {"minbo": 300, "qty": 1, "listings": 1, "at": "2026-11-09T00:00:00Z"},  # no market, value unknown
    }


def test_exports_while_the_game_runs(client, monkeypatch, capsys):
    # addon Lua files are never rewritten by the client, so a running game is no longer a blocker
    conn, root = client
    monkeypatch.setattr(export_tsm.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0))
    assert export_tsm.run(conn, root) == 0
    assert (root / "Interface/AddOns/ForeverMarketBridge/Data.lua").exists()
    assert "/reload picks it up" in capsys.readouterr().out


def test_patch_applies_to_pristine_api_lua(tmp_path):
    orig = LIVE_API.with_suffix(".lua.orig")
    pristine = orig if orig.exists() else LIVE_API
    if not pristine.exists() or "RegisterPriceSource" in pristine.read_text():
        pytest.skip("no pristine TSM App/API.lua on this machine")
    dest = tmp_path / "TradeSkillMaster/App/API.lua"
    dest.parent.mkdir(parents=True)
    shutil.copy(pristine, dest)
    # shortcut: falls back to git apply when GNU patch is not installed (atomic distro)
    cmd = ["patch", "--dry-run", "-p0"] if shutil.which("patch") else ["git", "apply", "--check", "-p0"]
    r = subprocess.run(cmd, stdin=PATCH.open(), cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
