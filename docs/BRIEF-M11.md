# M11 brief: the in-game market addon

Read `CLAUDE.md`, `docs/SPEC.md`, `docs/BRIEF-M10.md` and this brief.

Build a World of Warcraft addon, `ForeverMarketUI`, that renders the market window described
below from the SavedVariables table `ForeverMarketData` that `fm export addon` already writes.
This is a UI milestone: no new Python beyond two small export additions listed at the end.

Reference target (Life on Azeroth's auction house window), which we are matching in structure and
tone, not pixel for pixel:

- Dark charcoal window, thin gold border, small-caps gold headings, gold/silver coin icons.
- Title bar left `FOREVER MARKET`, red square close button top right.
- Item view: green header panel with gold border containing an item icon with gold border, the
  item name in green, two badges (`Trade good`, `Item level 25`), and on the right
  `Typical price · US · PvP` above a large price, with a gold outlined `+ Add to chart` button.
- Four equal stat cards: `Cheapest now`, `Auctions`, `Items for sale`, `Vendor pays`.
- Left panel 2/3 width, `PRICE HISTORY`, range buttons `6H | 1D | 1W | ALL`, legend
  `Typical price` (green swatch) and `Cheapest listing` (white swatch), a green line with a filled
  area under it, a white cheapest line, right-aligned gold y-axis labels, x-axis dates,
  an `Items for sale each hour` bar strip beneath, and the footer
  `Compared as % change from the start of the range`.
- Right sidebar 1/3 width: `PRICE IN EACH REGION` rows of `REGION | +x% vs cheapest | price` with
  the cheapest row highlighted, then `SIMILAR ON THE AUCTION HOUSE` with four rows of icon, name,
  price.
- Index view: a list of sectors with their percent change (Trade goods, Consumables, Armour,
  Weapons, Recipes, Other, and the aggregate `Forever 100`), a multi-line chart of the selected
  sectors over the chosen range, and the same range buttons.

## Data available

`ForeverMarketData` (SavedVariables, written hourly by the app):

```lua
{ generated, house, region,
  indices = { ["Trade goods"] = { {t=unix, v=84.2}, ... }, ["Forever 100"] = {...} },
  items   = { ["i:1234"] = { n=name, q=quality, il=ilvl, vendor=copper,
                             series={ {t=unix, typical=copper, cheapest=copper, qty=n, auctions=n}, ... },
                             regions = { us=copper, eu=copper, kr=copper, tw=copper } } } }
```

Treat every field as optional. If `ForeverMarketData` is nil or empty, the window must open and
say `No market data yet. Run fm export addon.` rather than erroring.

## Requirements

1. Files: `addon/ForeverMarketUI/ForeverMarketUI.toc` (`## Interface: 16001`,
   `## SavedVariables: ForeverMarketData`, `## OptionalDeps: TradeSkillMaster`) and Lua split into
   `Core.lua`, `Charts.lua`, `ItemView.lua`, `IndexView.lua`, `Util.lua`.
2. Window 820 x 580, movable, position and last selected item saved in a small
   `ForeverMarketUISettings` table (declare it in the toc), `UISpecialFrames` so ESC closes it.
3. Slash commands `/fm` and `/forevermarket` toggle it.
4. Index view is the default. Clicking a sector selects it for the chart, shift-click adds a
   second sector. Item view opens from a search box in the index header that filters item names
   as you type, and from clicking a row in the region or similar panels.
5. Charts drawn only with `Texture` strips and lines, no third-party libraries: area fill as one
   texture per pixel column tinted green with decreasing alpha, typical line as 1 px textures
   between consecutive points, cheapest line the same in white. Handle 1 point (flat line) and
   0 points (`No data`).
6. Range buttons filter the series by `t`: 6H, 1D, 1W, ALL. Default 1D.
7. Percentages: sector change is `(last/first - 1) * 100` from the visible range, green above
   zero, red below. Region rows show `+x% vs cheapest` computed from the per-item `regions` table,
   and mark the cheapest.
8. Money formatting: `38g 18s`, `75s`, `29c`, with the gold/silver/copper coin textures from
   `Interface\\MoneyFrame\\UI-GoldIcon`, `UI-SilverIcon`, `UI-CopperIcon`.
9. Theme: one colour table at the top of `Util.lua` (background `#141414` at 0.95 alpha, border
   `#c8a84b`, heading gold `#d8b96a`, body `#d9d9d9`, typical green `#4caf50`, cheapest white,
   negative red `#e05a4f`), so it can be retuned in one place.
10. No taint risk: do not touch secure frames, do not call protected functions, keep everything on
    a plain frame with `SetMovable`.

## Verification without the game

Add `addon/ForeverMarketUI/tests/stub.lua`, a fake WoW environment (`CreateFrame`, `Texture`,
`FontString`, `GameTooltip`, `C_Timer`, `UISpecialFrames`, `SlashCmdList`, `GetTime`,
`Interface\\...` strings, `format`, `floor`), and `addon/ForeverMarketUI/tests/smoke.lua` which
loads the addon files under it with a small synthetic `ForeverMarketData` (three items, 24 series
points, four regions, two indices) and asserts:

- the files load with no error and `/fm` handler is registered
- the chart module returns the expected number of strip textures for 24 points
- money formatting returns `38g 18s` for 381800 and `75s` for 7500
- percent change returns `-32.0` for 68 against 100
- the window builds with `ForeverMarketData = nil` without erroring

Run it with `luajit addon/ForeverMarketUI/tests/smoke.lua` and wire it into `uvx pytest -q` as a
subprocess test in `tests/test_m11.py` so the suite covers it.

## Two export additions

- add `c` (class id) and `s` (subclass id) to each exported item, for the similar-items panel
- add a `similar` helper is not needed; the addon derives similar items by same class/subclass and
  nearest price, and must cope with fewer than four matches

## Acceptance

```
luajit addon/ForeverMarketUI/tests/smoke.lua
uvx pytest -q
FM_FORCE_GAME_CLOSED=1 python3 -m fm export addon
```

Commit as `M11: ForeverMarketUI addon`. Do not install the addon into the game folder; the parent
agent does that. In the summary list the files, the smoke-test output, the export size, and every
place where the real data lacked a field the screenshot implies.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
