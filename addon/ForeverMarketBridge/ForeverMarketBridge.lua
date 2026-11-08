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

local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:SetScript("OnEvent", function(self, _, name)
	-- our own ADDON_LOADED: SavedVariables are only populated now, and TSM (a dependency) is already loaded
	if name ~= ADDON then return end
	self:UnregisterEvent("ADDON_LOADED")
	if ForeverMarketPrice == nil then return end
	register(RETRIES)
end)
