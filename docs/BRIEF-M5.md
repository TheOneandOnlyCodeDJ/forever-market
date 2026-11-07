# M5 brief

M1-M4 are committed and green (18 tests). Read `CLAUDE.md`, `docs/SPEC.md` and this brief.
This milestone is the reading surface: a local dashboard, still standard library only.

## Deliverables

1. `fm serve [--port 8099] [--host 127.0.0.1]`:
   - `http.server.ThreadingHTTPServer` with a custom handler, no framework, no new deps
   - routes: `/` dashboard, `/api/summary` returns `data/summary.json` as JSON, `/healthz` returns
     `ok`
   - `/` regenerates the report data from the DB on each request (cheap: it is one SQLite file)
     and renders HTML server-side; no client-side build step
2. Dashboard content, in this order, each as a section with a heading and a row count:
   - **header strip**: generated time, price timestamp for realm and region, kills and sessions
     imported, and a red `STALE` badge if any price source is older than 12 hours
   - **FARM**: the table from the digest, confidence as a colour chip, `thin` rows dimmed
   - **CRAFT**: top 15 by profit, HIDDEN rows marked
   - **FLIP**: top 15
   - **GATHER**: top 15 by node value
   - **KILL**: the measured per-source table
   - **Sources**: one line per sync source with its age
3. Styling: one inline `<style>`, dark background, monospace numbers, tables that do not wrap
   awkwardly, readable at 1200px. No external CSS, fonts or JS files.
4. `fm report --open` is out of scope. Instead print the URL when the server starts.
5. Tests, offline:
   - `build_html(data)` returns a string containing every section heading and the string `rows:`
     or a row count per section
   - the handler returns 200 and `text/html` for `/`, 200 and `application/json` for
     `/api/summary`, 404 for anything else (use a real server on port 0 in a thread)

## Rules

- Reuse `fm.report.build()` for the data; do not duplicate SQL in the web layer.
- The dashboard must render with an empty database too, showing `no data` in each section rather
  than crashing.
- Do not touch the digest format in this milestone.

## Acceptance

```
python3 -m fm serve --port 8099 &   # then curl -s localhost:8099 | head -40
curl -s localhost:8099/api/summary | head -c 200
uvx pytest -q
```

Show the first 40 lines of the HTML in your summary, confirm every section rendered with its row
count, and kill the server afterwards. Commit as `M5: local dashboard`.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
