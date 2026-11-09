-- Window, view switching, saved settings and slash commands. Plain frames only: nothing secure.
local ADDON, ns = ...
local U, C = ns.U, ns.C
local NAME = "ForeverMarketUIFrame"

local function tbl(v)
	return type(v) == "table" and v or {}
end

function ns.Data() return tbl(ForeverMarketData) end
function ns.Items() return tbl(ns.Data().items) end
function ns.Indices() return tbl(ns.Data().indices) end

local frame, empty, nav

local function show(view)
	local ok = (next(ns.Items()) or next(ns.Indices())) ~= nil
	ns.view = view
	U.Shown(empty, not ok)
	U.Shown(ns.IndexView.frame, ok and view == "index")
	U.Shown(ns.ItemView.frame, ok and view == "item")
	local last = ns.Items()[ns.S.item]
	U.Shown(nav, ok and (view == "item" or type(last) == "table"))
	if not ok then return end
	if view == "item" then
		nav.text:SetText("< Index")
		ns.ItemView.Refresh()
	else
		nav.text:SetText("Last: " .. tostring(type(last) == "table" and last.n or ns.S.item))
		ns.IndexView.Refresh()
	end
end

function ns.Refresh() show(ns.view or "index") end
function ns.ShowIndex() show("index") end

function ns.ShowItem(key, region)
	if type(ns.Items()[key]) ~= "table" then return end
	ns.S.item = key
	ns.ItemView.key, ns.ItemView.region = key, region
	show("item")
end

local function build()
	ForeverMarketUISettings = tbl(ForeverMarketUISettings)
	ns.S = ForeverMarketUISettings

	frame = CreateFrame("Frame", NAME, UIParent)
	frame:SetSize(820, 580)
	frame:SetFrameStrata("HIGH")
	U.Box(frame, C.bg, C.border)
	local p = tbl(ns.S.pos)
	if type(p[1]) == "string" and type(p[2]) == "string" and type(p[3]) == "number" and type(p[4]) == "number" then
		frame:SetPoint(p[1], UIParent, p[2], p[3], p[4])
	else
		frame:SetPoint("CENTER")
	end
	frame:SetMovable(true)
	frame:EnableMouse(true)
	frame:SetClampedToScreen(true)
	frame:RegisterForDrag("LeftButton")
	frame:SetScript("OnDragStart", frame.StartMoving)
	frame:SetScript("OnDragStop", function(self)
		self:StopMovingOrSizing()
		local point, _, rel, x, y = self:GetPoint()
		ns.S.pos = { point, rel, x, y }
	end)
	tinsert(UISpecialFrames, NAME) -- ESC closes it
	frame:Hide()

	local title = U.Text(frame, 13, C.heading)
	title:SetPoint("TOPLEFT", 12, -11)
	title:SetText("FOREVER MARKET")
	local rule = U.Tex(frame, "BORDER", C.border, 0.4)
	rule:SetHeight(1)
	rule:SetPoint("TOPLEFT", 1, -33)
	rule:SetPoint("TOPRIGHT", -1, -33)

	local close = U.Button(frame, 18, 18, nil, function() frame:Hide() end)
	close:SetPoint("TOPRIGHT", -8, -8)
	U.Box(close, C.close, C.border)
	local x = U.Text(close, 12, C.white, "CENTER")
	x:SetPoint("CENTER")
	x:SetText("x")

	nav = U.Button(frame, 200, 18, "", function()
		if ns.view == "item" then ns.ShowIndex() else ns.ShowItem(ns.S.item) end
	end)
	nav:SetPoint("RIGHT", close, "LEFT", -8, 0)

	empty = U.Text(frame, 14, C.body, "CENTER")
	empty:SetPoint("CENTER")
	empty:SetText("No market data yet. Run fm export addon.")

	local content = CreateFrame("Frame", nil, frame)
	content:SetSize(796, 528)
	content:SetPoint("TOPLEFT", 12, -40)
	ns.IndexView.Build(content)
	ns.ItemView.Build(content)
end

function ns.Toggle()
	if not frame then build() end
	if frame:IsShown() then
		frame:Hide()
	else
		frame:Show()
		show("index")
	end
end

SLASH_FOREVERMARKETUI1, SLASH_FOREVERMARKETUI2 = "/fm", "/forevermarket"
SlashCmdList.FOREVERMARKETUI = function() ns.Toggle() end
