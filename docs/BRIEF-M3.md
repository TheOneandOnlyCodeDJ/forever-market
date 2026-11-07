# M3 brief

M1 and M2 are committed and green. Read `docs/SPEC.md` (new section: **Measured loot import**),
`CLAUDE.md` and this brief. No addon gets written in this milestone: the addon already exists on
the machine and has data in it.

## Deliverables

1. `fm/lua_table.py`: a parser for WoW SavedVariables files. Input: file text. Output: a dict of
   top-level variable name -> Python value. It must handle what the client actually writes:
   `VAR = { ... }` assignments, CRLF, `["key"] = value` and `[123] = value`, bare `key = value`,
   nested tables, trailing commas, `true`/`false`, integers, floats, and strings with `\\"`,
   `\\\\`, `\\n` escapes plus `|cff...|Hitem:...|h[...]|h|r` colour codes kept verbatim.
   No `eval`, no Lua interpreter, no third-party parser.
2. `fm import loot [--dry-run]`:
   - glob `WTF/Account/*/*/SavedVariables/LootTrackerForever.lua` under the client path from
     `fm/paths.py` (new module; allow an env override `FM_CLIENT_DIR`)
   - for each file, take `LootTrackerForeverData.session` (the live session) and `history`
     (past sessions) and store them:
     - `loot_session(id PK, character, started, ended, kills, loots, copper, seconds, imported_at)`
       where `id` is `character + ':' + started`
     - `loot_source(session_id, name, kills, copper)`
     - `loot_item_source(session_id, source_name, item_id, count)`
     - `loot_item(session_id, item_id, count, vendor, name, quality)`
   - history entries carry no per-source detail; store them with `kills`, `copper`, `seconds` and
     `ended`, and leave the source tables empty for those sessions
   - `--dry-run` prints, per file: character, sessions found, kills, sources, items, and (if any)
     the strongest measured drop rate with kills >= 20. It writes nothing.
   - re-running is idempotent (upsert by session id, delete then insert children)
3. Digest section `KILL`, placed before `CRAFT`:
   - one row per source with `kills >= 5` from the most recent session per character:
     `source | kills | copper | copper/kill | best item | rate | sample`
   - `best item` = highest `count/kills` item for that source, `rate` as a percent with one
     decimal, `sample` = kills
   - footer: sessions imported, characters, total kills
   - if no loot data exists at all, the section renders one line `no loot data yet` and still
     ends with `rows: 0`
4. `MEASURED` table inside KILL: items where `kills >= 20` and `count >= 2`, columns
   `item | source | kills | drops | rate %`, top 25 by rate, followed by
   `measured rates are local to this realm and character`.
5. Tests, offline, with a fixture SavedVariables file in `tests/fixtures/` that contains two
   characters, one session each, escaped strings, a colour-code link and a nested source table:
   - parser round-trip on that fixture
   - drop-rate arithmetic: 8 kills, 2 drops -> 25.0%
   - idempotent re-import (import twice, row counts unchanged)
   - KILL renders `no loot data yet` when the db is empty and `rows: 0`

## Acceptance

```
python3 -m fm import loot --dry-run
python3 -m fm import loot
python3 -m fm report
uvx pytest -q
```

Print the KILL section and the row counts. Commit as `M3: import measured loot from Loot Tracker Forever`.

In the summary state: which characters and sessions were imported, total kills, how many sources
cleared `kills >= 5`, and the top three measured drop rates with their sample sizes. If the real
files yield nothing, say so plainly instead of inventing data.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
