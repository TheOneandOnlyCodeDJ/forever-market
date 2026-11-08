# M8 brief: one house, correctly identified

M7 is committed, credentials are live in `.env`, and a Horde sync has already run. Read
`CLAUDE.md`, `docs/SPEC.md` and this brief.

## What the live data showed (do not re-derive it)

The five Horde houses are **not** the same market, so the current `API` section is wrong: it
aggregates all of them. From the sync on 2026-11-08:

| house | auctions | commodities | distinct items with a buyout |
| --- | --- | --- | --- |
| 113 | 141,217 | 69,008 | 3,096 |
| 114 | 155,350 | 62,618 | 3,001 |
| 115 | 0 | 0 | empty |
| 120 | 19,026 | 11,605 | 1,549 |
| 124 | 26,291 | 20,532 | 1,881 |

Added together that is 348,644 auctions, which is meaningless. Blackwater houses 116, 117, 121,
125 are small and 118 is empty.

Matching each house against the local TSM realm file (`price_realm.min_buyout`) to guess which
one is the player's realm:

| house | common items | exact minBO match | median relative difference |
| --- | --- | --- | --- |
| 113 | 2,397 | 29% | 0.21 |
| 114 | 2,381 | 29% | 0.20 |
| 120 | 1,486 | 18% | 0.50 |
| 124 | 1,779 | 20% | 0.38 |
| Blackwater | 178-785 | 8-15% | 0.54-0.67 |

113 and 114 both look plausible; the player is Horde on the PvP ruleset.

## Deliverables

1. `fm api match`:
   - for every house that has auctions, compute against `price_realm.min_buyout`: common items,
     exact matches (within 1 copper), and the median relative difference
   - print a ranked table and a recommended house id
   - persist the result in a small table `api_house_match(house_id PK, common, exact, median_diff,
     scored_at)` so the report can use it without recomputing
2. `fm sync api` gains `--house <id>` to sync a single house, and keeps the current behaviour when
   no id is given.
3. `API` section fixes:
   - use **exactly one house**, chosen in this order: `FM_API_HOUSE` from the environment, then the
     best row of `api_house_match` with `common >= 50`, then the house with the most auctions
   - header states the house id and name, and the footer states `single house only: the five
     Horde houses are separate markets and are never summed`
   - keep the existing columns; add `api listings` (number of auction rows for that item in that
     house) between `api qty` and `tsm market`
   - if no API data exists, keep `no api data yet` and `rows: 0`
4. `fm api probe` bug: the ruleset index prints `None` for names. Inspect the real payload shape
   (it is cached in `data/cache/` if the sync stored it, otherwise print the raw key names) and
   print the id with whatever name field exists, or `-`.
5. Tests: house scoring maths on a fixture; single-house selection order (env override, then best
   match, then most auctions); empty house skipped; `api listings` column present; probe name
   fallback when the field is missing.
6. Dashboard: add an `API` section to `fm serve` with the same single-house table.

## Acceptance

```
python3 -m fm api match
python3 -m fm report && sed -n '/## API/,/## WATCH/p' reports/digest.md
uvx pytest -q
```

Run against the live database, print the match table and the corrected API section, and commit as
`M8: single auction house, matched to the realm`. In the summary give the recommended house, its
exact-match percentage, and the top five rows of the corrected section.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
