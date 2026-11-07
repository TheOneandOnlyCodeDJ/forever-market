# M1 brief

Build milestone 1 of `forever-market` in this repo. Read `docs/SPEC.md` and `CLAUDE.md` first.

## Deliverables

1. `fm/` package with: `__main__.py` (argparse), `db.py`, `http.py`, `fmt.py`, `schema.sql`,
   `sync_prices.py`, `sync_items.py`, `report.py`.
2. `fm.db` creates `data/market.db` and applies `fm/schema.sql` idempotently.
3. `python3 -m fm sync prices` fetches both TSM CSVs through `fm/http.py` and upserts
   `price_realm` and `price_region`. Print a one-line summary per source: rows written and the
   file's `updatedAt`.
4. `python3 -m fm sync items` fetches `Item`, `ItemSparse` (Forever, build 1.60.1.70790) and
   `ItemSparse` (Classic Era, build 1.15.9.70576), merges them with Forever winning, and
   populates `item`. Same one-line summary.
5. `python3 -m fm report` writes:
   - `reports/digest.md` with sections `SNAPSHOT`, `GATHER`, `FLIP`, `WATCH`, each table ending
     in `rows: N`, plus a header block listing every source's `updatedAt` and the row counts.
   - `data/summary.json` with the same data, keys documented in a `_meta` block.
6. `pytest -q` with real tests: schema applied twice is a no-op; copper->gold formatting;
   digest generated from `tests/fixtures/market_fixture.db` contains the four section headers
   and finite row counts; `fm.http` respects the cache (second call does not hit disk twice,
   verified with a stub).

## Fixtures

`tests/fixtures/` needs: `pvp_horde_items.csv` and `forever_us_items.csv` (5-10 rows each,
real column headers), and `market_fixture.db` built by a `tests/make_fixture.py` script from
those CSVs plus a handful of items, so `fm report` can run offline in tests.

## Data details you will need

- TSM `updatedAt` is ISO-8601 UTC and identical for every row in a file; store it once per
  sync in `sync_log` and stamp the digest header from there.
- `marketValue` can be `0` for items with no scan data. Treat `0` as unknown for reporting
  (skip in the market summary, show `-` in tables) but store it as given.
- Forever `ItemSparse` is incomplete: 19,307 rows against 31,986 in `Item`. Items missing from
  both ItemSparse exports get `name = 'item <id>'` and `source = 'missing'`.
- `Item.csv` supplies `ClassID`/`SubclassID`; `ItemSparse` supplies name, quality
  (`OverallQualityID`), `ItemLevel`, `RequiredLevel`, `Bonding`, `Stackable`.

## GATHER table definition

Rows: items with `class_id = 7` (Trade Goods) that have a realm price above 0.
Columns: `item | type | market | minBO | region sale | node value`. Subclass names:
5 Cloth, 6 Leather, 9 Herb, 10 Elemental, 7 Ore/Stone, 8 Meat, 12 Enchanting, 11 Other, 1 Parts.
Node value = market x 1.5 for herbs, x 2.2 for ore, x 1.0 for leather/cloth, `-` otherwise.

## FLIP table definition

Rows: realm items with `market_value >= 10000` copper (1g) and
`min_buyout <= 0.7 * market_value`. Columns: `item | market | minBO | gap | gap %`.
Sort by gap descending, cap 25 rows.

## Acceptance

Run, from the repo root:

```
python3 -m fm sync prices && python3 -m fm sync items && python3 -m fm report && pytest -q
```

Network may or may not be reachable; if a fetch fails, still finish the rest and leave the DB
usable, and say exactly which source failed in the summary. Then print the first 40 lines of
`reports/digest.md` and the row counts, and commit.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
