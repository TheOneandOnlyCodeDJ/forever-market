# forever-market

Market data for World of Warcraft Forever. The contract is `docs/SPEC.md`. Run `python3 -m fm <subcommand>`.

## Prices inside TSM

`python3 -m fm export tsm` writes the matched house's official-API prices to
`WTF/Account/<acct>/SavedVariables/ForeverMarketPrice.lua`. It refuses (exit 3) while `Wow.exe` runs.
The `addon/ForeverMarketBridge` addon loads that file and registers three TSM price sources:

- `api`: Forever API min buyout per unit
- `apilist`: Forever API listing count
- `fmvalue`: Forever market value (max of 0.95 x realm min buyout and vendor price)

Example: an Auctioning min price of `max(90% api, fmvalue)`.

### Local TSM patch

TSM has no public way to register a price source, so this repo patches TSM's `App/API.lua` to add
`TSM_API.RegisterPriceSource(key, label, callback)`. **A TSM update reverts the patch.** Re-apply it
with the game closed:

```
cd "<client>/Interface/AddOns"
cp TradeSkillMaster/App/API.lua TradeSkillMaster/App/API.lua.orig
patch -p0 < /path/to/forever-market/addon/tsm-patches/API.lua.patch   # or: git apply -p0 ...
```

Install the bridge by copying `addon/ForeverMarketBridge` into `Interface/AddOns`. If the patch is
missing, the bridge prints a red warning naming `TSM_API.RegisterPriceSource` in chat.

## Hourly history and the addon data feed

`fm sync prices` and `fm sync api` each append one snapshot per hour to `price_history` (a second run in
the same hour replaces it). `fm sync prices` also writes `index_history`: per item class,
`100 x median(market now / market at the first snapshot)`, skipped below 20 items.

`fm sync api --regions us,eu,kr,tw --house best` fetches one house per region. Only the home region
(`BLIZZARD_REGION`, default `us`) lands in the `api_*` tables; other regions go to `price_history` only,
because house ids repeat across regions.

`fm export addon` writes `WTF/Account/<acct>/SavedVariables/ForeverMarketData.lua` (up to 2,000 items,
168 hourly points each). While `Wow.exe` runs it writes `ForeverMarketData.pending.lua` instead and
promotes it on the next run with the game closed.

### Hourly timer

The systemd user units in `deploy/` assume the repo is at `~/Projects/forever-market`:

```
mkdir -p ~/.config/systemd/user
cp deploy/forever-market-sync.service deploy/forever-market-sync.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now forever-market-sync.timer
journalctl --user -u forever-market-sync.service     # logs
```

The timer writes SavedVariables only when the client is closed: with the game open, `export tsm` is
skipped and `export addon` writes only the pending file.
