"""Local dashboard: `fm serve`. Server-side HTML from fm.report.build(), standard library only."""
import json
from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fm import db, report
from fm.db import ROOT

STALE_HOURS = 12
CHIP = {"ok": "#2e7d32", "thin": "#b26a00"}
STYLE = """
body{background:#111418;color:#d8dde3;font:14px/1.4 system-ui,sans-serif;margin:24px;max-width:1400px}
h1{font-size:20px;margin:0 0 8px}h2{font-size:16px;margin:28px 0 6px;border-bottom:1px solid #2a3038}
h2 small{color:#8a94a0;font-weight:normal;margin-left:8px}
table{border-collapse:collapse;width:100%}th,td{padding:3px 10px;text-align:left;white-space:nowrap;
border-bottom:1px solid #1e242b}th{color:#8a94a0;font-weight:600;position:sticky;top:0;background:#111418}
td.n{text-align:right;font-family:ui-monospace,Menlo,Consolas,monospace}tr:hover td{background:#1a1f26}
tr.thin td{opacity:.55}.hidden{color:#e0b84a;font-weight:600}
.chip{display:inline-block;padding:0 7px;border-radius:8px;color:#fff;font-size:12px}
.strip{display:flex;flex-wrap:wrap;gap:18px;background:#181c22;padding:10px 14px;border-radius:6px}
.strip b{color:#8a94a0;font-weight:normal;margin-right:4px}
.stale{background:#c62828;color:#fff;padding:1px 8px;border-radius:4px;font-weight:700}
.empty{color:#8a94a0;font-style:italic}.mono{font-family:ui-monospace,Menlo,Consolas,monospace}
"""


def _parse(ts):
    """'2026-11-07T19:16:23Z' or sqlite '2026-11-07 21:25:37' (UTC) -> aware datetime, else None."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    except (AttributeError, ValueError):
        return None


def _age(ts, now):
    t = _parse(ts)
    if t is None:
        return None
    return (now - t).total_seconds() / 3600


def _age_text(hours):
    if hours is None:
        return "-"
    return f"{hours * 60:.0f}m" if hours < 1 else f"{hours:.1f}h" if hours < 48 else f"{hours / 24:.1f}d"


def _section(title, cols, rows, row_class=None, cell=None):
    out = [f"<h2>{escape(title)}<small>rows: {len(rows)}</small></h2>"]
    if not rows:
        return out + ['<p class="empty">no data</p>']
    out.append("<table><tr>" + "".join(f"<th>{escape(c)}</th>" for c in cols) + "</tr>")
    for r in rows:
        cls = row_class(r) if row_class else ""
        tds = []
        for c in cols:
            html = cell(c, r) if cell else None
            if html is None:
                v = r[c]
                html = escape(report._fmt(c, v))
                if isinstance(v, (int, float)) or v is None:
                    html = f'<td class="n">{html}</td>'
                else:
                    html = f"<td>{html}</td>"
            tds.append(html)
        out.append(f'<tr class="{cls}">' + "".join(tds) + "</tr>")
    return out + ["</table>"]


def _cell(c, r):
    if c == "confidence":
        v = r[c]
        return f'<td><span class="chip" style="background:{CHIP.get(v, "#555")}">{escape(v)}</span></td>'
    if c == "item" and str(r[c]).startswith("HIDDEN "):
        return f'<td><span class="hidden">HIDDEN</span> {escape(r[c][7:])}</td>'
    return None


def build_html(data, generated_at=None, now=None):
    now = now or datetime.now(timezone.utc)
    generated_at = generated_at or now.strftime("%Y-%m-%dT%H:%M:%SZ")
    src = {s["source"]: s for s in data["sources"]}
    strip, stale = [], False
    for name in ("tsm_realm", "tsm_region"):
        s = src.get(name)
        # price timestamp = TSM updatedAt at the start of note; a FAILED or missing sync counts as stale
        ts = (s["note"] or "").split(" ")[0] if s else ""
        ts = ts if _parse(ts) else None
        age = _age(ts, now)
        stale |= age is None or age > STALE_HOURS
        strip.append(f'<span><b>{name[4:]} prices</b><span class="mono">{escape(ts or "-")}</span>'
                     f" ({_age_text(age)})</span>")
    t = data["kill_totals"]
    strip = [f'<span><b>generated</b><span class="mono">{escape(generated_at)}</span></span>', *strip,
             f'<span><b>kills</b><span class="mono">{t["kills"] or 0}</span></span>',
             f'<span><b>sessions</b><span class="mono">{t["sessions"] or 0}</span></span>']
    if stale:
        strip.append(f'<span class="stale">STALE</span> <span>a price source is older than {STALE_HOURS}h or missing</span>')
    sources = [{"source": s["source"], "fetched_at": s["fetched_at"],
                "age": _age_text(_age(s["fetched_at"], now)), "rows": s["rows"], "note": s["note"]}
               for s in data["sources"]]
    cols = report.COLUMNS
    body = [
        "<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
        "<title>forever-market</title>", f"<style>{STYLE}</style></head><body>",
        "<h1>forever-market</h1>", '<div class="strip">' + "".join(strip) + "</div>",
        *_section("FARM", cols["farm"], data["farm"],
                  row_class=lambda r: "thin" if r["confidence"] == "thin" else "", cell=_cell),
        *_section("CRAFT", cols["craft"], data["craft"][:15], cell=_cell),
        *_section("FLIP", cols["flip"], data["flip"][:15]),
        *_section("GATHER", cols["gather"], data["gather"][:15]),
        *_section("KILL", cols["kill"], data["kill"]),
        *_section("Sources", ["source", "fetched_at", "age", "rows", "note"], sources),
        "</body></html>",
    ]
    return "\n".join(body)


class Handler(BaseHTTPRequestHandler):
    db_path = db.DB_PATH
    summary_path = ROOT / "data" / "summary.json"

    def _send(self, code, ctype, body):
        body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            conn = db.connect(self.db_path)
            try:
                self._send(200, "text/html", build_html(report.build(conn)))
            finally:
                conn.close()
        elif path == "/api/summary":
            try:
                text = self.summary_path.read_text()
            except FileNotFoundError:
                return self._send(404, "application/json", json.dumps({"error": "run `fm report` first"}))
            self._send(200, "application/json", text)
        elif path == "/healthz":
            self._send(200, "text/plain", "ok")
        else:
            self._send(404, "text/plain", "not found")


def serve(host="127.0.0.1", port=8099):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"serving http://{host}:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
