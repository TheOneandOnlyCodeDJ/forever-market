# M10 brief: hourly collection, history, and the addon data feed

M1-M9 are committed and green (41 tests). Credentials are live, house 113 is the matched US Horde
house, and `fm export tsm` already writes `ForeverMarketPrice.lua` for the TSM bridge. Read
`CLAUDE.md`, `docs/SPEC.md` and this brief first.

Goal: an in-game addon (M11) that looks like Life on Azeroth's auction house window needs history,
not a snapshot. This milestone builds the data behind it and the hourly collection that keeps it
fresh. No addon code in this milestone.

## 1. History tables

Add to the schema:

```sql
price_history(at TEXT, source TEXT, house_id INTEGER, item_id INTEGER,
              min_buyout INTEGER, market INTEGER, listings INTEGER, qty INTEGER,
              PRIMARY KEY (at, source, house_id, item_id))
index_history(at TEXT, category TEXT, index_value REAL, PRIMARY KEY (at, category))
```

- `source` is `api` or `tsm`. `at` is the snapshot hour, ISO-8601 UTC truncated to the hour, so a
  second sync inside the same hour updates rather than duplicates.
- `fm sync api` and `fm sync prices` each append one snapshot per run for the rows they already
  write. Do not change existing tables.
- `index_history` is derived: for each category, take items present in both the current snapshot
  and the first snapshot of the series, and store `100 * median(price_now / price_first)`. Keep
  `REAL` here, it is an index not money.

Categories by item class: `Trade goods` (7), `Consumables` (0), `Armour` (4), `Weapons` (2),
`Recipes` (9), `Other`. Plus one aggregate `Forever 100` across every item with a price in both.
Require at least 20 items in a category before writing its index, otherwise skip it and say so.

## 2. Multi-region support

`fm sync api` already takes `--region`. Extend the sync so a single run can cover several:

- `fm sync api --regions us,eu,kr,tw --house best` fetches only the best-matching (or largest)
  Horde house per region, not all five, to keep bandwidth sane. A house per region is one request
  pair and about 9 MB.
- store region in `api_house` (add a `region TEXT` column, backfill `us`) and in `price_history`
  via `source = 'api:<region>'`, or add a `region` column. Prefer the explicit column.
- print per-region counts.

## 3. `fm export addon`

Writes `WTF/Account/<acct>/SavedVariables/ForeverMarketData.lua`, table `ForeverMarketData`,
compact enough to stay under about 2 MB of Lua:

```lua
ForeverMarketData = {
  generated = "2026-11-10T06:00:00Z",
  house = 113, region = "us",
  regions = { us = 1, eu = 1, kr = 1, tw = 1 },          -- cheapest seen per region, copper
  indices = { ["Trade goods"] = { {t=<unix>, v=84.2}, ... }, ["Forever 100"] = {...} },
  items = {
    ["i:1234"] = {
      n = "Cerulean Dye", q = 1, il = 25, vendor = 7500,
      series = { {t=<unix>, typical=381800, cheapest=293600, qty=513, auctions=173}, ... },
    },
  },
}
```

- `series` keeps the last 168 hourly points per item (one week).
- `items` covers: every item in the top 300 by API min buyout, every item already in
  `forever-market` groups, and everything with a measured drop. Cap at 2,000 items, sorted
  deterministically.
- `regions` holds the cheapest listing per region for that item when regional data exists.
- Refuse to write while `Wow.exe` is running: write `ForeverMarketData.pending.lua` instead and
  print one line saying it will be promoted on the next run. When the client is closed and a
  pending file exists, move it into place first.
- Print: items, series points total, byte size, and whether it promoted a pending file.

## 4. Hourly service

`deploy/forever-market-sync.service` and `.timer` (systemd user units, checked into the repo, not
installed):

```
fm sync prices && fm sync api --regions us,eu,kr,tw --house best && fm sync api-history
fm report && fm export tsm && fm export addon
```

- `OnCalendar=hourly`, `Persistent=true`, `RandomizedDelaySec=120`.
- Document installation in the README as `systemctl --user enable --now`, with `journalctl` for
  logs, and state that the timer writes SavedVariables only when the client is closed.

## 5. Tests, offline

- history append is idempotent within an hour (run twice, same row count)
- index maths: two snapshots with a known ratio give the expected index value, and a category
  with 19 items writes no index
- export round-trips through `fm/lua_table.py`, respects the 2,000 item cap and the 168 point
  window, and writes `.pending.lua` when `FM_FORCE_GAME_RUNNING=1`
- promotion path: pending file exists plus `FM_FORCE_GAME_CLOSED=1` moves it into place

## Acceptance

```
FM_FORCE_GAME_CLOSED=1 python3 -m fm sync prices
FM_FORCE_GAME_CLOSED=1 python3 -m fm sync api --regions us --house best
FM_FORCE_GAME_CLOSED=1 python3 -m fm export addon
uvx pytest -q
```

Print the export summary line and the size of the generated file, list the index categories
written with their current values, and commit as `M10: hourly history and addon data feed`.

In the summary state: rows in `price_history`, categories indexed, items exported, file size, and
anything that contradicts this brief. Do not install the systemd units and do not start the timer.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
