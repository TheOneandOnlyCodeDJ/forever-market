import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fm import db, fmt, http, report  # noqa: E402

FIXTURE_DB = ROOT / "tests" / "fixtures" / "market_fixture.db"


def _schema(conn):
    return conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()


def test_schema_applied_twice_is_noop(tmp_path):
    path = tmp_path / "m.db"
    conn = db.connect(path)
    first = [tuple(r) for r in _schema(conn)]
    db.log_sync(conn, "x", 1, "kept")
    conn.close()
    conn = db.connect(path)
    assert [tuple(r) for r in _schema(conn)] == first
    assert len(first) == len(report.TABLES) == 13
    assert conn.execute("SELECT note FROM sync_log").fetchall()[0][0] == "kept"


def test_gold_formatting():
    assert fmt.gold(1234567) == "123.46g"
    assert fmt.gold(10000) == "1.00g"
    assert fmt.gold(1) == "0.00g"
    assert fmt.gold(0) == "-"
    assert fmt.gold(None) == "-"


def test_digest_from_fixture_db(tmp_path):
    conn = sqlite3.connect(FIXTURE_DB)
    conn.row_factory = sqlite3.Row
    data = report.run(conn, tmp_path / "digest.md", tmp_path / "summary.json")
    md = (tmp_path / "digest.md").read_text()
    for section in ("## SNAPSHOT", "## GATHER", "## FLIP", "## WATCH"):
        assert section in md
    counts = [int(line.split()[1]) for line in md.splitlines() if line.startswith("rows: ")]
    assert len(counts) == 7 and all(n > 0 for n in counts)  # every table non-empty on fixtures
    gather = {r["item"]: r for r in data["gather"]}
    assert gather["Peacebloom"]["node value"] == 33  # 22c x 1.5
    assert gather["Copper Ore"]["node value"] == 132  # 60c x 2.2
    assert [r["item"] for r in data["flip"]] == ["Large Knapsack", "Recipe: Wildvine Potion", "Barbaric Shoulders"]
    assert data["watch"] == [{"item": "Elixir of Minor Fortitude", "reason": "recipe output"}]
    assert '"_meta"' in (tmp_path / "summary.json").read_text()


def test_http_uses_cache(tmp_path, monkeypatch):
    calls = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return b"itemId\n1\n"

    def fake_urlopen(req, timeout):
        calls.append(req.full_url)
        return Resp()

    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(http, "MIN_DELAY", 0)
    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    url = "https://example.invalid/items.csv"
    assert http.get(url) == b"itemId\n1\n"
    assert http.get(url) == b"itemId\n1\n"
    assert calls == [url]
    assert http.get(url, ttl=0) == b"itemId\n1\n"  # expired cache refetches
    assert len(calls) == 2
