# Project context

`forever-market` tracks the World of Warcraft Forever auction house and world data so a human
and an LLM can decide what to farm, craft or flip. Read `docs/SPEC.md` before writing code; it
is the contract. This file only adds working rules.

## Conventions

- Python 3.11+ **standard library only**. If a dependency feels necessary, stop and say so in
  your summary instead of adding it.
- Layout: `fm/` package, `tests/`, `data/` (gitignored except fixtures), `reports/` (gitignored),
  `addon/` for the Lua logger, `docs/`.
- Entry point: `python3 -m fm <subcommand>`. Keep argument parsing in `fm/__main__.py`.
- SQLite access through `fm/db.py` (one connection factory, schema applied on first use).
- Anything that leaves the machine goes through `fm/http.py` (cache + delay + UA). Tests never
  call it; they use `tests/fixtures/*.csv`.
- Prices are copper everywhere in code and DB. Convert to gold only at the formatting layer
  (`fm/fmt.py`), which formats `1234567` as `123.46g`.
- Unknowable values stay `None`, never `0`.
- Commit in small logical commits with messages like `M1: add price sync`.

## Gates before you call a milestone done

```
python3 -m fm sync prices   # against fixtures via --fixtures flag, or real network if available
python3 -m fm report
pytest -q
```

`reports/digest.md` must exist, have the sections named in SPEC.md, and end each table with
`rows: N`. Report the numbers you saw, not adjectives.

## Do not

- Do not edit `docs/SPEC.md` or this file.
- Do not commit `data/*.db`, `data/cache/`, or `reports/`.
- Do not invent drop rates, yields or prices. `NULL` is correct when data is missing.
- Do not add a web framework for the dashboard in M1.
