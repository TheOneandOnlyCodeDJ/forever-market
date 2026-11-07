# M4 brief

M1-M3 are committed and green. Read `CLAUDE.md`, `docs/SPEC.md` (Measured loot import section) and
this brief. This milestone turns measured drops into money: what a kill is actually worth.

## Deliverables

1. `KILL` gains two columns, right of `copper/kill`:
   - `loot/kill` = sum over that source's items of `count x price / kills`, where price is realm
     `market_value`, falling back to region `market_value`, and 0 when neither exists; print how
     many drops had no price at all in the footer
   - `total/kill` = `copper/kill + loot/kill`
   Both formatted with `fm.fmt.coin` (gold above 1g, else silver, else copper).
2. New section `FARM`, after KILL and before CRAFT:
   - header line with pace: `kills/hour` and `gold/hour` from the session that produced the rows,
     using `loot_session.elapsed` and the whole session's loot value; state the session it came
     from and how long it ran
   - table of sources with `kills >= 10`, sorted by `total/kill` descending, cap 25:
     `source | kills | total/kill | loot share | best item | rate | confidence`
   - `loot share` = percent of that source's loot value from its best item
   - `confidence` = `ok` at kills >= 50, `thin` at 10-49
   - footer: total sources considered, how many were dropped for low sample, and the price
     coverage percent (priced drops / all drops) for the rows shown
3. `data/summary.json` gains `farm` with the same fields plus the raw copper values.
4. Tests, offline:
   - EV maths: a source with 20 kills, one item at 25% and 100 copper price, 500 copper coin ->
     `loot/kill` 500, `copper/kill` 500, `total/kill` 1000 copper, printed `10.00s`
   - unpriced drop counts reach the footer and `price coverage` reflects it
   - `confidence` boundary: 49 kills is `thin`, 50 is `ok`
   - a source at 9 kills does not appear in FARM

## Rules

- One source of truth for prices: a helper `price_of(conn, item_id)` in `fm/report.py` returning
  `(copper, source)` where source is `realm`, `region` or `none`. Use it for KILL and FARM so the
  two can never disagree.
- Do not change the existing KILL columns' order or meaning.
- No network in tests and no new dependencies.

## Acceptance

```
python3 -m fm report && python3 -m fm status && uvx pytest -q
```

Print the KILL and FARM sections. Commit as `M4: value per kill and farm ranking`. In the summary
give the top five sources by `total/kill` with kills and confidence, the session pace line, and
the price coverage percent.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
