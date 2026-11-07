# forever-market

Market intelligence for World of Warcraft Forever (US, PvP-Horde). Prices, drop rates,
gathering data and craft margins in one SQLite database, with human dashboards and a
compact digest written for an LLM to read.

## Hard rules

- **Python 3.11+ standard library only** for everything in `fm/`. No requests, no pandas, no
  ORM. `sqlite3`, `urllib`, `csv`, `json`, `argparse`, `datetime` are enough and keep the
  install trivial on an atomic distro.
- Every network fetch goes through `fm/http.py`, which caches raw responses under
  `data/cache/` with a TTL and a per-host minimum delay. Nothing else calls the network.
- Every figure in a report carries its unit. Copper in the DB, gold in reports, percent as
  0-100 where labelled, 0-1 where labelled `rate`.
- No fabricated data. If a number is unknown, it is `NULL` in SQLite and `-` in reports.
- Tests must not touch the network. Fixtures live in `tests/fixtures/`.

## Data sources (all verified reachable on 2026-11-07)

1. **TSM public data**, plain CSV over HTTPS, no auth:
   - realm: `https://public-data.tradeskillmaster.com/forever/us/realm/pvp-horde/items.csv`
     columns `itemId,name,marketValue,minBuyout,recent,historical,updatedAt`
   - region: `https://public-data.tradeskillmaster.com/forever/us/region/items.csv`
     columns `itemId,name,marketValue,historical,avgSalePrice,saleRate,soldPerDay,updatedAt`
   - All prices in copper.
2. **wago.tools DB2 exports**, CSV per table for a given build:
   `https://wago.tools/db2/<Table>/csv?build=1.60.1.70790`
   Verified present: `Item`, `ItemSparse`, `ItemSearchName`, `SpellName`, `SpellEffect`,
   `SpellReagents`, `SkillLineAbility`, `Creature`, `AreaTable`, `SpellItemEnchantment`.
   **Not present** for this build: `GameObject`, `CreatureLoot` (loot is server-side).
3. **Classic Era ItemSparse** (`build=1.15.9.70576`) as a metadata fallback: the Forever
   `ItemSparse` export only names ~19.3k of ~32k items. Merge Era underneath Forever.
4. **Wowhead Forever** (`https://www.wowhead.com/forever/...`) for creatures, drop rates and node
   locations. This is the only workable world-data source: the client DB2 `Creature` export for
   build 1.60.1 holds only 185 rows and `CreatureLoot`/`GameObject` do not exist at all, so
   creatures, drops and nodes must come from Wowhead plus our own logging. Cloudflare blocks
   plain curl (403); the browser tool or a real UA works. Cache hard, resume, never hammer.
5. **Local game data** (authoritative for this realm, cannot be scraped):
   - TSM SavedVariables:
     `/home/bazzite/Faugus/battlenet/drive_c/Program Files (x86)/World of Warcraft/_forever_/WTF/Account/250808230#1/SavedVariables/TradeSkillMaster.lua`
     holds his own auction scans, craft DB and prices.
   - Our own loot addon (see `addon/`) writes kill + loot events for measured drop rates.

## Measured loot import (Loot Tracker Forever)

`LootTrackerForever` is already installed on the client and writes one SavedVariables file per
character: `WTF/Account/<acct>/<realm>/<Char>/SavedVariables/LootTrackerForever.lua`, table
`LootTrackerForeverData`. Structure verified on 2026-11-07 (Lain: 320 kills, 441 loots, 50 sources):

```lua
LootTrackerForeverData = {
  session  = { started, lastActive, elapsed, copper, kills, loots,
               sources = { ["<creature or node name>"] = { kills, copper, items = { [itemID] = count } } },
               items   = { [itemID] = { count, vendor, name, q, cat, first, last, link } },
               zones   = { ["<zone>"] = n }, rares = {...}, feed = {...} },
  history  = { { ended, valueSource, items, copper, kills, seconds }, ... },   -- last N sessions
  lifetime = { sessions, total, copper, kills, seconds, bestPerHour, bestTotal },
}
```

Measured drop rate for an item from a source is `items[itemID] / sources[name].kills`, with
`sources[name].kills` as the sample size. Nothing here is vendor-normalised: `copper` is the
looted coin only, item value is in `items[id].vendor` (or the addon's configured price source).

`LootGoblin` is a different addon and only writes scan diagnostics; ignore it.

## Database

`data/market.db`, schema in `fm/schema.sql`. Tables:

- `item(id PK, name, quality, item_level, req_level, class_id, sub_class, bonding, stackable,
   vendor_sell, source)` - `source` is `forever` or `era` so merged rows stay honest.
- `price_realm(item_id PK, market_value, min_buyout, recent, historical, updated_at)`
- `price_region(item_id PK, market_value, historical, avg_sale, sale_rate, sold_per_day, updated_at)`
- `spell(id PK, name, profession, min_skill, category_id)`
- `spell_reagent(spell_id, item_id, quantity)`
- `craft_output(spell_id, item_id, num_result)` - from `SpellEffect` effect 24.
- `creature(id PK, name, min_level, max_level, classification, creature_type, area_id)`
- `area(id PK, name, parent_id, continent_id)`
- `drop(creature_id, item_id, chance, source, sample_size)` - `source` is `wowhead` or `local`.
- `kill_event(id PK, creature_id, at, duration_s, source)` - measured kill times.
- `loot_event(id PK, kill_event_id, item_id, quantity)` - measured loot.
- `node_area(item_id, area_id, kind, source)` - gathering: which material spawns where (kind
  `herb`, `ore`, `skin`, `fish`).
- `sync_log(source, fetched_at, rows, note)`

## Commands

```
fm sync prices          # TSM realm + region CSVs -> price tables
fm sync items           # wago Item/ItemSparse(+Era) -> item table
fm sync recipes         # Spell/SpellEffect/SpellReagents/SkillLineAbility -> spell + reagents
fm sync world           # Creature, AreaTable -> creature/area (levels, zones)
fm sync all
fm import tsm           # parse TSM SavedVariables for his own scans/prices
fm import loot <path>   # our addon's SavedVariables -> kill_event/loot_event
fm report               # writes reports/digest.md + reports/dashboard.html + data/summary.json
fm serve                # local dashboard on :8099
fm status               # row counts + last sync per source
```

## Reports

`reports/digest.md` is the AI-facing artifact. It must be stable, dense and table-first:

1. Header with data timestamps per source and row counts, so staleness is obvious.
2. Market snapshot: item count, total listed value, median, the 10g+ band, biggest movers vs
   `historical`.
3. `GATHER` table: material, price, min buyout, region sale rate, value per node (price x
   classic yield: herb 1.5, ore 2.2, skin 1.0).
4. `KILL` table: creature, level, area, expected loot value per kill (sum of
   `chance x price`), measured median kill time where available, gold/hour estimate with the
   formula shown.
5. `CRAFT` table: item, profession, skill, material cost, sell price after 5% cut, profit,
   margin percent, and whether it is already listed (so "hidden" recipes stand out).
6. `FLIP` table: realm items where `min_buyout << market_value`, with the gap.
7. `WATCH` list: items with no price data that are recipe outputs or notable drops.
8. Every table ends with `rows: N` so a reader can tell it was not truncated.

`data/summary.json` mirrors the digest in machine-readable form with identical field names.

## Milestones

- **M1** scaffold, schema, `sync prices`, `sync items`, `report` with snapshot + gather + flip.
- **M2** recipes/craft margins, world sync, node areas.
- **M3** loot addon (`addon/ForeverLootLogger`) + `import loot`, measured kill times/rates.
- **M4** wowhead drop-rate ingestion (cached, rate-limited, resumable).
- **M5** dashboard (`fm serve`) with tables and sparklines, plus `WATCH`/`ALERT` rules.

## Acceptance for each milestone

- `python3 -m fm <cmd>` runs from the repo root with no arguments beyond the command.
- `pytest -q` green, no network, fixtures only.
- `reports/digest.md` regenerates from the DB alone (no network) and every table is non-empty
  against the checked-in fixture DB.
- `git status` clean of stray files; no `data/cache/*.csv` committed.
