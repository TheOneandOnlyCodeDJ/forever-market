# M7 brief: official Blizzard API (WoW Forever)

Read `CLAUDE.md` and `docs/SPEC.md` first. M1-M6 are committed and green.

The Forever API went live for auctions on 2026-11-06 and is undocumented; the field notes below
come from probing and from the `blizzard_api` library. Implement against them, but code
defensively: every response shape can change without notice.

## Credentials

Read from `.env` in the repo root (add `.env` to `.gitignore`):

```
BLIZZARD_CLIENT_ID=...
BLIZZARD_CLIENT_SECRET=...
BLIZZARD_REGION=us
```

OAuth: `POST https://oauth.battle.net/token` with `grant_type=client_credentials`, basic auth
with id/secret. Cache the token at `data/cache/blizzard_token.json` with its expiry and reuse it
until 120 seconds before expiry. Without credentials, every API command must exit with a clear
one-line message and code 2, never a traceback, and `fm report` must still work.

Data host per region: `https://{region}.api.blizzard.com`, region in `us, eu, kr, tw`.
Every request needs `?namespace=dynamic-forever-{region}` (auctions and rulesets) and
`Accept-Encoding: gzip`. Send a real `User-Agent` and a 0.2s minimum delay between calls.

## Endpoint shapes (verified by third parties, treat as provisional)

```
/data/wow/ruleset/index                          -> { rulesets: [{ id, name }] }
/data/wow/ruleset/{id}                           -> { id, name, auctions, status }
/data/wow/ruleset/{id}/auctions/                 -> { auctions: [{ key.href, name, id }] }   NOTE trailing slash
/data/wow/ruleset/{id}/auctions/{houseId}        -> { id, name, auctions: [...], commodities: [...], ruleset }
/data/wow/ruleset/{id}/auctions/{houseId}/commodities -> { auctions: [{ id, item{id}, quantity, unit_price, time_left }] }
```

House ids are 110-121 and 123-125: five Alliance, five Horde, five Blackwater. Some houses have
no `auctions` field at all (112, 115, 118 seen empty) so treat it as optional. Every ruleset
returns the same houses with identical auctions, so **analyse exactly one ruleset** and say so in
the report footer. Auction entries: `id, item{id, context, bonus_lists, modifiers}, buyout, bid?,
quantity, time_left`. Commodities carry `unit_price` instead of `buyout`. A single house can be
50k-68k auctions, roughly 9 MB, so do not fetch all fifteen by default.

`/data/wow/item/{id}` 404s for roughly 43% of auction item ids on Forever. Resolve names from the
local `item` table instead and count the misses; never fail a sync on an unresolved id.

## Deliverables

1. `fm/blizzard.py`: `token()`, `get(path, namespace=..., region=...)`, both testable without
   network through an injectable transport. Raise `BlizzardError` with status and body snippet.
2. `fm api probe`: prints the ruleset index, then the auction house index for `--ruleset`
   (default 1), then the house list with ids and names. Tiny output, no DB writes.
3. `fm sync api [--ruleset 1] [--houses horde|all] [--region us]`:
   - resolve the ruleset, fetch the auction house index with the trailing slash, keep houses whose
     name contains `Horde` and `Blackwater` by default (`--houses all` keeps everything)
   - for each kept house, fetch `/auctions/{id}` and `/commodities`, insert into:
     - `api_house(house_id PK, ruleset_id, name, faction, auctions, commodities, fetched_at)`
     - `api_auction(house_id, auction_id, item_id, quantity, buyout, bid, unit_price, time_left, captured_at)`
       with PK (house_id, auction_id); a sync replaces that house's rows wholesale
     - `api_commodity(house_id, item_id, quantity, unit_price, captured_at)`
   - print: houses fetched, auctions, commodities, distinct item ids, ids missing from `item`
4. `API` section in the digest, after FLIP and before WATCH:
   - Horde houses only, per item: `min(buyout)`, `sum(quantity)`, plus local TSM `market_value`
     and `min_buyout` where present, and the percent difference against TSM market
   - columns: `item | api minBO | api qty | tsm market | diff %`; top 20 by api minBO; footer with
     houses used, auctions read, unresolved ids, and `one ruleset only: houses are identical
     across rulesets`
   - renders `no api data yet` plus `rows: 0` with no rows, so the empty-DB test still passes
5. Tests, offline: ruleset index parse; house index with the trailing slash built correctly; a
   house with no `auctions` key handled; commodity `unit_price` parsing; auction row upsert
   replaces stale rows; unresolved item id counted not raised; token cached and reused (stub
   transport counts calls); missing credentials exits 2 with one line.
6. SPEC: add an "Official API" source section with these shapes, the trailing-slash rule, the
   "never sum across rulesets" rule, and the 43% item-lookup caveat.

## Acceptance

```
uvx pytest -q
python3 -m fm report            # API section shows "no api data yet" without creds
python3 -m fm api probe; echo "exit=$?"   # clean exit 2 and one line without creds
```

If `.env` happens to hold real credentials by the time you run, also run `fm api probe` and
`fm sync api --houses horde` once and paste the counts, but never commit `.env` or any token.

Commit as `M7: official Forever API ingest`. In the summary state what the probe printed, the
counts if you had credentials, and anything in the response shapes that contradicted this brief.

If a rule here contradicts `docs/SPEC.md`, say so in one line before implementing.
