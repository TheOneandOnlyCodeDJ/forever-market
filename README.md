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
