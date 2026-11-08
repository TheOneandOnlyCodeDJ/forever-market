import json
import shutil
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fm import db, report, web  # noqa: E402

SECTIONS = ["FARM", "BOE", "CRAFT", "FLIP", "GATHER", "KILL", "API house - (-)", "Sources"]


def test_build_html_empty_db(tmp_path):
    html = web.build_html(report.build(db.connect(tmp_path / "e.db")))
    for s in SECTIONS:
        assert f"<h2>{s}<small>rows: 0</small></h2>" in html
    assert html.count("no data") == len(SECTIONS)
    assert "STALE" in html  # no price source at all


def test_build_html_fixture_db(tmp_path):
    shutil.copy(ROOT / "tests" / "fixtures" / "market_fixture.db", tmp_path / "f.db")
    conn = db.connect(tmp_path / "f.db")
    data = report.build(conn)
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    html = web.build_html(data, now=now)
    for s in SECTIONS:
        assert f"<h2>{s}<small>rows: " in html
    assert f"<h2>CRAFT<small>rows: {min(15, len(data['craft']))}</small>" in html
    assert "STALE" in html  # fixtures are years older than `now`


def test_handler_routes(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"ok": 1}))
    handler = type("H", (web.Handler,), {"db_path": tmp_path / "s.db", "summary_path": summary,
                                         "log_message": lambda *a: None})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        for path, ctype in (("/", "text/html"), ("/api/summary", "application/json"), ("/healthz", "text/plain")):
            with urllib.request.urlopen(base + path) as r:
                assert r.status == 200 and r.headers["Content-Type"].startswith(ctype)
        try:
            urllib.request.urlopen(base + "/nope")
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
        server.server_close()
