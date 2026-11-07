# M6 brief

M1-M5 are committed and green. Read `CLAUDE.md`, `docs/SPEC.md` and this brief.

Two changes, both about valuing drops honestly: every item has a guaranteed vendor floor, and
bind-on-equip gear belongs in the pool instead of being discarded for having no market price.

## 1. Item value with a vendor floor

Add to `fm/report.py`:

```python
def value_of(conn, item_id) -> tuple[int, str]:
    """(copper, source) with source in {"buyout", "vendor", "none"}"""

buyout = 0.95 * realm min_buyout when min_buyout > 0      # what you can actually get after the cut
vendor = item.vendor_sell                                  # guaranteed
value  = max(buyout, vendor)  -> source "buyout" if buyout >= vendor and buyout > 0, else "vendor"
value  = 0                    -> source "none"
```

`item.vendor_sell` is already populated from `ItemSparse.SellPrice` (20,963 items), so use it,
do not re-sync. Region market is **not** a valuation source any more; keep it only for the
`listed`/`sale rate` columns.

Use `value_of` in KILL, FARM and MEASURED so all three agree. Footer changes from "drops with no
price" to:

```
value source: buyout 61%, vendor 37%, none 2% (n drops)
```

## 2. Bind-on-equip pool and a BOE section

`item.bonding = '2'` means bind on equip. Those can be sold, so they must not be excluded just
because the realm has no listing.

New section `BOE`, after FARM and before CRAFT:

- rows: items with `bonding = '2'`, `quality >= 2`, dropped by a source or produced by a recipe
  (union of `loot_item_source.item_id` and `craft_output.item_id`), with `value > vendor`
  OR `value >= 5000` copper
- columns: `item | ilvl | q | vendor | buyout | value | premium | listings | sale rate | flag`
- `premium` = `value / vendor` as `x.x` when vendor > 0, else `-`
- `listings` = realm `min_buyout > 0` count for that item, 1 if present (per-item, so `yes`/`no`)
- `sale rate` = region `sale_rate`, 3 decimals, `-` when absent
- `flag`, one per row, checked in this order:
  - `scarce` when no realm listing and `value >= 20000` (2g) - nobody is selling it
  - `demand` when region `sale_rate >= 0.25`
  - `thin` when there is a listing but region sale rate is missing or below 0.05
  - `vendor` otherwise, meaning it is worth vendor price only
- sort by `value` descending, cap 20 rows, footer: candidates, how many were dropped for
  `source = none`, and a one-line note that flags are price-and-liquidity signals, not proof of
  buyer interest.

## 3. Tests, offline

- `value_of` returns `("buyout", ...)` when `0.95 x minBO > vendor`, `("vendor", ...)` when vendor
  wins, `("none", 0)` when both are zero
- a BoE item with no listing and value 2.5g renders `scarce`
- a BoE item with sale rate 0.31 renders `demand`
- an item with `bonding = '1'` never appears in BOE
- KILL loot/kill uses the vendor floor: a 1-kill source dropping a 100-copper-vendor item with no
  market price values it at 100, not 0

## Acceptance

```
python3 -m fm report && python3 -m fm status && uvx pytest -q
```

Print KILL, FARM and BOE. Commit as `M6: vendor floor valuation and BoE pool`. In the summary give
the value-source split, how many BoE rows rendered, and the three highest-value BoE drops with
their flags.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
