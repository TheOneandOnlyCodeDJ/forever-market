# Audit, 2026-11-10

Scope: `fm/*.py`, `fm/schema.sql`, `addon/ForeverMarketUI/*.lua`, `addon/ForeverMarketBridge/*`,
`addon/tsm-patches/*`, `deploy/*`, `tests/*`. Reviewed by reading, plus live checks against the
real database and the installed client.

## Fixed in this pass

| severity | file:line | finding | action |
| --- | --- | --- | --- |
| bug | fm/report.py:241 `pick_house` | the fallback query required `auctions > 0`, so a house whose last pull returned zero rows could not be selected at all, and the addon export then produced an empty file with no error | fixed: any known house, ordered by `COALESCE(auctions, 0) DESC` |
| bug | fm/export_addon.py | coverage was capped by item count (2,000) rather than bytes, so the file shipped 422 of 4,415 priced items and the addon looked empty | fixed: tier 1 hourly (top 500 + measured drops), tier 2 daily, byte cap 3 MB, `res` field per item |
| bug | fm/export_addon.py `_series` | the function depended on a TEMP table created by its caller, so calling it directly failed and it was one refactor away from a silent empty series | fixed: it creates and fills `export_ids` itself |
| bug | fm/doctor.py `checks` | `offline=False` default shadowed `FM_DOCTOR_OFFLINE`, so the env var did nothing and every run hit the token endpoint | fixed: default `None`, resolved from the environment |
| risk | live TSM 4.15.5 update, 2026-11-10 03:19 | **both** local patches were reverted silently: `TSM_API.RegisterPriceSource` gone, and the `TSM-Ref` exemption in `ProfessionScanner.lua` gone, which means the 2,292 injected craft rows would be pruned at the next login and the crafting tooltips would disappear again | fixed: `fm patch-tsm` reapplies both from anchors, `fm doctor` reports each one, and the hourly service now repairs them before exporting |
| risk | fm/history.py + price_history | no retention; about 9,500 rows an hour, forever | fixed: `fm prune`, hourly 7 days, one row per day to 90 days |
| style | addon/ForeverMarketUI | `res` was not present in the data contract before this pass, so the UI could not distinguish hourly from daily series | fixed on both sides |

## Left as designed, with the reason

| severity | area | note |
| --- | --- | --- |
| risk | fm/history.py index baseline | indices are `100 * median(now / first)`. `fm prune` deletes old rows, so after 7 days the `first` snapshot moves forward and the index rebases to 100 again. Acceptable while the series is young; a fixed epoch would be needed for a permanent index. |
| risk | addon series | `typical` comes from the TSM market file (roughly 3 hourly) while `cheapest` and `qty` come from the API (hourly). Two cadences are drawn as one chart line; the footer says so on purpose. |
| risk | api_auction | holds one snapshot per house, replaced wholesale on each sync. Deliberate: 324k rows per house would otherwise multiply per region per hour. |
| risk | export promotion | a pending file is only promoted when `Wow.exe` is closed, by design, because the client rewrites SavedVariables at logout. |
| risk | addon charts | the Lua side has no pruning of its own; it trusts the 168 point window from the exporter. A larger export is only ever slower to load. |
| risk | fm/prune.py | day boundaries are UTC, not realm time, so "the last row of a day" can fall at a realm-time offset. |
| risk | report BOE flags | `scarce` and `demand` are liquidity and price signals, not evidence of buyers. Stated in the section header. |
| risk | `.env` | holds a live Blizzard client secret in plaintext, mode 600. That is the minimum for a local service; a keyring would be the next step. |
| style | tests | the `patch --dry-run` check skips when GNU `patch` is absent (it is absent here), falling back to `git apply --check`. |

## Not verified

- The addon has never rendered inside the game. It is verified only through the stubbed smoke test
  (56 checks), which cannot catch anchoring, texture paths or font issues.
- No API endpoint beyond rulesets, houses, auctions, commodities and a character profile has been
  exercised. Statistics categories and `/experience` are empty or 404 on Forever.
- The hourly timer has run twice by hand; it has not yet fired on its own schedule with the game
  closed, which is the only path that promotes a pending export.

## Numbers at audit time

```
item 31,986   price_realm 5,048   price_history 18,924   api_auction 324,077
export: 4,455 items (622 hourly, 3,833 daily), 4,914 series points, 696,630 bytes
tests: 55 passed, 1 skipped
doctor: 16 checks, 0 failing
```
