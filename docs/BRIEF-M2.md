# M2 brief

Milestone 1 is committed: `fm sync prices`, `fm sync items`, `fm report` and 4 tests all work
against live data. Read `docs/SPEC.md` (I amended source 2 and 4 since M1) and `CLAUDE.md`.

Scope change from SPEC's milestone list: **do not build `fm sync world` yet.** The client DB2
`Creature` export has only 185 rows for this build and `CreatureLoot`/`GameObject` do not
exist, so creature, drop and node data have to come from Wowhead plus our own loot logging.
That is M4. Keep the `creature`, `area`, `drop`, `node_area` tables in the schema unused for now.

## Deliverables

1. `fm sync recipes`:
   - fetch `SpellName`, `SpellEffect`, `SpellReagents`, `SkillLineAbility` for build 1.60.1.70790
     through `fm/http.py`
   - `spell(id, name, profession, min_skill, category_id)` from `SpellName` +
     `SkillLineAbility`. Profession skill lines: 171 Alchemy, 164 Blacksmithing, 333 Enchanting,
     202 Engineering, 185 Cooking, 129 First Aid, 165 Leatherworking, 197 Tailoring, 186 Mining,
     356 Fishing. A spell appearing more than once keeps the lowest `MinSkillLineRank`.
   - `spell_reagent(spell_id, item_id, quantity)` from `SpellReagents` columns `Reagent_0..7`
     and `ReagentCount_0..7`, skipping zero ids and zero counts.
   - `craft_output(spell_id, item_id, num_result)` from `SpellEffect` rows with `Effect = 24`
     and `EffectItemType > 0`. `num_result` = `EffectBasePointsF`, clamped to 1..200, default 1.
   - skip spells with no reagents. Print one line: spells, reagents rows, outputs rows.
2. New `CRAFT` section in the digest, between GATHER and FLIP:
   - one row per output item, for the spell with the lowest material cost
   - `cost` = sum over reagents of `quantity x price`, using realm price first and region
     price as fallback; a row whose every mat is priced by realm alone gets no marker,
     otherwise `*` after the profession name
   - `sell` = 0.95 x realm market value (5% AH cut), `profit` = sell - cost,
     `margin %` = 100 x profit / cost
   - `listed` = `yes` when the realm has `min_buyout > 0` for the output, else `no`
   - `HIDDEN` marker in the first column when `profit > 0` and `listed = no` (a profitable
     craft nobody is selling)
   - columns: `item | profession | skill | cost | sell | profit | margin % | listed | sale rate`
   - sort by profit descending, cap 30 rows, then print a one-line footer with how many outputs
     were skipped for unpriced materials
3. `fm status`: prints per-source last fetch and row counts for every table. (SPEC lists it and
   M1 did not build it.)
4. Tests, offline:
   - `SkillLineAbility` fixture with one spell listed twice at min ranks 50 and 100 resolves to 50
   - `SpellEffect` fixture with `EffectBasePointsF` 0, 1 and 200 clamps to 1, 1 and 200
   - craft margin maths: cost 100 copper, market 200 copper -> sell 190, profit 90, margin 90%
   - a HIDDEN case: profit > 0 and no realm `min_buyout`
   - GATHER regression: `Copper Bar` and `Bolt of Linen Cloth` never appear in GATHER

## Acceptance

```
python3 -m fm sync recipes && python3 -m fm report && python3 -m fm status && uvx pytest -q
```

Then print the CRAFT section of `reports/digest.md` (or its first 20 lines) and the row counts,
commit with `M2: recipes and craft margins`, and in your summary state how many outputs had all
materials priced, how many were skipped, and the top five by profit.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
