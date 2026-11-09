import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from fm import db, export_addon  # noqa: E402


def test_addon_smoke_under_luajit():
    if not shutil.which("luajit"):
        pytest.skip("luajit not installed")
    r = subprocess.run(["luajit", "addon/ForeverMarketUI/tests/smoke.lua"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "checks passed" in r.stdout


def test_export_carries_class_and_subclass(tmp_path):
    conn = db.connect(tmp_path / "m.db")
    conn.execute("INSERT INTO item (id, name, class_id, sub_class) VALUES (1, 'Dye', 7, 5), (2, 'Unclassed', NULL, NULL)")
    conn.executemany("INSERT INTO loot_item_source VALUES ('s', 'mob', ?, 1)", [(1,), (2,)])
    items = export_addon.build(conn)[0]["items"]
    assert (items["i:1"]["c"], items["i:1"]["s"]) == (7, 5)
    assert "c" not in items["i:2"] and "s" not in items["i:2"]  # unknown stays nil
