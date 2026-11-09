-- Registers forever-market's exported API prices (ForeverMarketPrice) as TSM price sources.
-- Needs the local TSM patch in addon/tsm-patches/API.lua.patch, which adds TSM_API.RegisterPriceSource.
local ADDON = ...
local SOURCES = {
	{ "api", "minbo", "Forever API min buyout" },
	{ "apilist", "listings", "Forever API listings" },
	{ "fmvalue", "value", "Forever market value" },
}
local RETRIES = 5

local function lookup(field)
	return function(itemString)
		local row = ForeverMarketPrice[itemString] or ForeverMarketPrice[itemString:match("^i:%d+") or ""]
		return row and row[field]
	end
end

local function register(triesLeft)
	local api = _G.TSM_API
	if not (api and api.RegisterPriceSource) then
		if triesLeft > 0 then
			C_Timer.After(0, function() register(triesLeft - 1) end)
		else
			print("|cffff4040ForeverMarketBridge: TSM_API.RegisterPriceSource is missing. Re-apply addon/tsm-patches/API.lua.patch (a TSM update reverts it).|r")
		end
		return
	end
	for _, s in ipairs(SOURCES) do
		api.RegisterPriceSource(s[1], s[3], lookup(s[2]))
	end
	local n = 0
	for _ in pairs(ForeverMarketPrice) do n = n + 1 end
	print(format("ForeverMarketBridge: %d items loaded, sources api, apilist, fmvalue", n))
end

-- Data.lua is loaded before this file, so the price table is already populated: no SavedVariables
-- and no event needed. TSM is a hard dependency, so TSM_API exists by now; retry a few frames anyway
-- in case a future TSM changes its load order.
if type(ForeverMarketPrice) == "table" then
	register(RETRIES)
else
	print("|cffffa000ForeverMarketBridge: no price data yet. Run fm export tsm and /reload.|r")
end

