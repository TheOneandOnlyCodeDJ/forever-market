# M9 brief: expose API prices inside TSM

M1-M8 are committed and green (38 tests). Credentials are live in `.env` and house 113 is the
matched auction house. Read `CLAUDE.md`, `docs/SPEC.md` and this brief.

## Why this needs a patch

TSM computes price sources from its own databases only. It has no HTTP, no file watcher, and
`LibTSMTypes` is not registered with LibStub, so an outside addon cannot call
`CustomString.RegisterSource` directly. The one clean entry point is `App/API.lua`, which TSM
already loads as its "Public APIs" file and which already imports `CustomString`. TSM's own
addon table is the global `TradeSkillMaster`, so an outside addon can reach it as
`_G.TradeSkillMaster.App.API`.

So: one small patch to TSM plus one tiny companion addon plus an exporter in this repo.

## Deliverables

1. `fm export tsm`:
   - writes `WTF/Account/<acct>/SavedVariables/ForeverMarketPrice.lua` inside the client dir from
     `fm/paths.py`, table name `ForeverMarketPrice`:
     ```lua
     ForeverMarketPrice = {
       ["i:1234"] = { minbo = 1234, qty = 5, listings = 2, market = 5000, value = 5000, at = "2026-11-09T00:00:00Z" },
     }
     ```
   - `minbo` = api per-unit min buyout, `qty` = sum quantity, `listings` = auction rows,
     `market` = local `price_realm.market_value` (omitted when absent), `value` = `value_of()`
   - only items that have api data; sort keys for stable output
   - **refuse to write while `Wow.exe` is running** (`pgrep -x Wow.exe`), same rule as the TSM
     patch: print one line and exit 3
   - print rows written and the path
2. Companion addon at `addon/ForeverMarketBridge/`:
   - toc: `## Interface: 16001`, `## Title: ForeverMarketBridge`, `## Dependencies: TradeSkillMaster`,
     `## SavedVariables: ForeverMarketPrice`
   - Lua: on `ADDON_LOADED` for TradeSkillMaster (retry a few frames if `App.API.RegisterPriceSource`
     is missing), register three sources through `_G.TradeSkillMaster.App.API`:
     - `api` = `minbo`, label `Forever API min buyout`
     - `apilist` = `listings`, label `Forever API listings`
     - `fmvalue` = `value`, label `Forever market value`
   - print one chat line on success with the number of items loaded, and a clear warning naming the
     missing API method if registration fails, so the failure is visible instead of silent
   - do nothing when `ForeverMarketPrice` is nil
3. Patch `App/API.lua` in the live addon folder (documented as a local patch):
   ```lua
   ---Registers an external price source.
   function API.RegisterPriceSource(key, label, callback)
       CustomString.RegisterSource("ForeverMarket", key, label, callback, CustomString.SOURCE_TYPE.NORMAL)
   end
   ```
   Keep a copy of the patched file in `addon/tsm-patches/API.lua.patch` (a unified diff) so it can
   be re-applied after a TSM update, and note in the README that a TSM update reverts it.
4. Tests, offline: the exporter output round-trips through `fm/lua_table.py`; items without api
   rows are excluded; `market` omitted when absent; `pgrep` guard is skipped when `FM_SKIP_PGRP=1`
   so tests run headless; the diff file applies cleanly to a pristine copy of `App/API.lua`
   (test with `patch --dry-run` against the backup).
5. README section "Prices inside TSM" with the three source names and a one-line example formula.

## Acceptance

```
FM_SKIP_PGRP=1 python3 -m fm export tsm
python3 -c "from fm import lua_table; print(len(lua_table.parse(open('<the file>').read())['ForeverMarketPrice']))"
uvx pytest -q
patch --dry-run -p0 < addon/tsm-patches/API.lua.patch
```

Print the row count and the first three keys. Commit as `M9: API prices as TSM price sources`.

In the summary state the row count, whether the patch applied, and anything about TSM's API
surface that contradicted this brief. Do not restart the game, do not touch SavedVariables other
than the new file.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
