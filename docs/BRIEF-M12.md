# M12 brief: audit and close the known gaps

Read `CLAUDE.md`, `docs/SPEC.md`, `docs/BRIEF-M10.md` and `docs/BRIEF-M11.md`. M1-M11 are
committed, 47 tests pass, and the addon has a stubbed smoke test.

Two jobs: audit what exists, then close the four gaps below. The audit findings go in a file, the
fixes go in commits. Do not rewrite the architecture; this is a review pass with targeted repairs.

## 1. `docs/AUDIT.md`

Read every one of `fm/*.py`, `fm/schema.sql`, `addon/ForeverMarketUI/*.lua`,
`addon/ForeverMarketBridge/*`, `addon/tsm-patches/*`, `deploy/*`, `tests/*`. For each real problem
write a row:

| severity | file:line | finding | action |

- severity: `bug`, `wrong number`, `risk`, `dead code`, `style`
- `action`: `fixed`, `documented`, or `left` with one clause of reasoning

Look specifically for: SQL that silently drops rows (`LEFT JOIN` turning into an inner join),
percentages computed against a zero or missing baseline, prices treated as gold where copper is
meant, sync paths that can overwrite another region's rows, Lua that can nil-index on real data,
SavedVariables writes without the `Wow.exe` guard, and any number in the reports that cannot be
traced to a table.

Fix everything you score as `bug` or `wrong number`. Do not change behaviour that is merely a
design choice; list it with `left`.

## 2. Addon data coverage

`fm export addon` currently ships 422 items because it takes the API top 300 plus measured drops,
while the API returns 4,415 priced items. Cover everything, within a hard size budget:

- tier 1: full hourly series (168 points) for the top 500 by API min buyout
- tier 2: daily-downsampled series (last 90 days, one point per day) for every other item with an
  API price
- hard cap 3,000,000 bytes on the generated file; when over, drop tier 2 items from the cheapest
  end until it fits, and print how many were dropped
- keep the existing per-item shape so the addon needs no change, but add `res` = `"h"` or `"d"` so
  the UI can say the series is daily

## 3. History retention

`price_history` grows about 9,500 rows an hour and never shrinks. Add `fm prune`:

- keep hourly rows for 7 days
- keep one row per day (the last of that day) for 90 days
- delete everything older than 90 days
- print rows before, deleted, after
- wire it into `deploy/forever-market-sync.service` after the syncs, and add a test with a
  fixture covering each of the three buckets

## 4. `fm doctor`

One command that answers "is this install healthy", each line `ok`, `warn` or `fail`:

- credentials present in `.env`, token fetchable (do not print the secret)
- TSM patch applied (`TSM_API.RegisterPriceSource` present in the live `App/API.lua`)
- bridge addon installed in `Interface/AddOns/ForeverMarketBridge`
- `ForeverMarketPrice.lua` and `ForeverMarketData.lua` exist, their age in hours, and whether a
  `.pending` file is waiting
- both timers active, with next elapse times
- price staleness: TSM realm `updatedAt` age and API snapshot age
- row counts for the four biggest tables

Exit 0 when nothing is `fail`, 1 otherwise. It must never write anything.

## Acceptance

```
uvx pytest -q
python3 -m fm export addon        # with the game closed, or accept the pending path
python3 -m fm prune
python3 -m fm doctor; echo "exit=$?"
```

In your summary: the audit table's counts by severity, the export coverage and size before and
after, prune numbers, and the doctor output. Commit as `M12: audit, coverage, retention, doctor`.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
