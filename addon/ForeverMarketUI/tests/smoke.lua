-- luajit addon/ForeverMarketUI/tests/smoke.lua
local dir = arg[0]:match("^(.*)[/\\]tests[/\\][^/\\]+$") or ".."
local checks = 0
local function ok(cond, what)
	checks = checks + 1
	if not cond then error("FAIL: " .. what, 2) end
	print("ok - " .. what)
end
local function eq(got, want, what)
	ok(got == want, what .. " (got " .. tostring(got) .. ", want " .. tostring(want) .. ")")
end

local function fresh(data, settings)
	for _, g in ipairs({ "ForeverMarketUIFrame", "SLASH_FOREVERMARKETUI1", "SLASH_FOREVERMARKETUI2" }) do _G[g] = nil end
	ForeverMarketData, ForeverMarketUISettings = data, settings
	local stub = dofile(dir .. "/tests/stub.lua")
	return stub.load(dir), stub
end

local T0 = 1794178800 - 23 * 3600
local function series(base)
	local s = {}
	for i = 0, 23 do
		s[#s + 1] = { t = T0 + i * 3600, typical = base + i * 100, cheapest = base - 500 + i * 50, qty = 100 + i, auctions = 10 + i }
	end
	return s
end
local function index(first, last)
	local s = {}
	for i = 0, 23 do s[#s + 1] = { t = T0 + i * 3600, v = first + (last - first) * i / 23 } end
	return s
end
local function sample()
	return {
		generated = "2026-11-10T06:00:00Z", house = 113, region = "us",
		indices = { ["Trade goods"] = index(100, 68), ["Forever 100"] = index(100, 110) },
		items = {
			["i:1"] = { n = "Cerulean Dye", q = 2, il = 25, vendor = 7500, c = 7, s = 5, series = series(381800),
				regions = { us = 293600, eu = 301800, kr = 352300, tw = 440400 } },
			["i:2"] = { n = "Crimson Dye", q = 1, il = 20, vendor = 29, c = 7, s = 5, series = series(200000) },
			["i:3"] = { n = "Copper Sword", c = 2, s = 7, series = {} },
		},
	}
end

-- 1. no data at all: the window still builds and says so
local ns = fresh(nil, nil)
eq(SLASH_FOREVERMARKETUI1, "/fm", "/fm is registered")
eq(SLASH_FOREVERMARKETUI2, "/forevermarket", "/forevermarket is registered")
ok(type(SlashCmdList.FOREVERMARKETUI) == "function", "slash handler is a function")
SlashCmdList.FOREVERMARKETUI("")
ok(ForeverMarketUIFrame and ForeverMarketUIFrame:IsShown(), "window builds and opens with ForeverMarketData = nil")
ok(not ns.IndexView.frame:IsShown() and not ns.ItemView.frame:IsShown(), "both views stay hidden without data")
eq(UISpecialFrames[1], "ForeverMarketUIFrame", "ESC closes it (UISpecialFrames)")
SlashCmdList.FOREVERMARKETUI("")
ok(not ForeverMarketUIFrame:IsShown(), "second /fm closes it")
fresh({}, nil)
SlashCmdList.FOREVERMARKETUI("")
ok(ForeverMarketUIFrame:IsShown(), "window opens with an empty ForeverMarketData")
fresh({ items = { ["i:9"] = {}, ["i:8"] = 5 }, indices = { Other = "x" } }, { pos = "junk", item = "i:9" })
SlashCmdList.FOREVERMARKETUI("")
ns = select(1, fresh({ items = { ["i:9"] = {} } }, { item = "i:9" }))
SlashCmdList.FOREVERMARKETUI("")
ns.ShowItem("i:9")
ok(ns.ItemView.frame:IsShown(), "an item with no fields at all still renders")

-- 2. formatting and maths
local U = ns.U
eq(U.Money(381800), "38g 18s", "money 381800")
eq(U.Money(7500), "75s", "money 7500")
eq(U.Money(29), "29c", "money 29")
eq(U.Money(nil), "-", "money nil")
ok(U.Money(381800, true):find("UI%-GoldIcon") and U.Money(381800, true):find("UI%-SilverIcon"), "money with coin textures")
eq(U.Pct(68, 100), -32.0, "percent change 68 against 100")
eq(U.Pct(5, 0), nil, "percent change against zero is unknown")

-- 3. charts
local chart = ns.Charts.New(UIParent, 164, 64, tostring)
eq(chart.plotW, 100, "plot is 100 px wide")
local pts = {}
for i = 0, 23 do pts[#pts + 1] = { t = T0 + i * 3600, v = i * i } end
local n = chart:Draw({ { pts = pts, color = ns.C.green, fill = true }, { pts = pts, color = ns.C.white } })
eq(n.fill, 100, "24 points: one fill strip per pixel column")
eq(n.line, 200, "24 points: one line strip per column per series")
n = chart:Draw({ { pts = { { t = T0, v = 5 } }, color = ns.C.green, fill = true } })
eq(n.line, 100, "1 point draws a full-width line")
local flat = true
for i = 1, n.line do flat = flat and chart.line[i].h == 1 and chart.line[i]:IsShown() end
ok(flat, "1 point line is flat")
ok(not chart.line[101]:IsShown(), "strips from the previous draw are released")
n = chart:Draw({ { pts = {}, color = ns.C.green, fill = true } })
ok(n.fill == 0 and n.line == 0 and chart.none:IsShown(), "0 points shows No data")
eq(ns.Charts.Bars(UIParent, 100, 20):Draw(pts), 24, "bar strip has one bar per point")

-- 4. the real window on synthetic data
local stub
ns, stub = fresh(sample(), nil)
SlashCmdList.FOREVERMARKETUI("")
local IV, XV = ns.ItemView, ns.IndexView
ok(XV.frame:IsShown() and not IV.frame:IsShown(), "index view is the default")
eq(ns.range, 2, "default range is 1D")
eq(XV.counts.line, XV.chart.plotW, "index chart draws the one selected sector")
eq(XV.rows[2].pct:GetText(), "-32.0%", "Trade goods sector change over the range")
eq(XV.rows[1].pct:GetText(), "+10.0%", "Forever 100 sector change over the range")
eq(XV.rows[3].pct:GetText(), "-", "sector without an index shows -")
XV.rows[2]:Click()
ok(XV.selected["Trade goods"] and not XV.selected["Forever 100"], "click selects one sector")
stub.shift = true
XV.rows[1]:Click()
stub.shift = false
eq(XV.counts.line, 2 * XV.chart.plotW, "shift-click adds a second sector")
XV.ranges.buttons[1]:Click()
eq(XV.rows[2].pct:GetText(), "-10.9%", "6H range: 68 against 76.35 over the 7 visible points")
XV.ranges.buttons[2]:Click()

XV.box:SetText("dye")
eq(XV.Search("dye"), 2, "search filters item names")
eq(XV.hits[1].name:GetText(), "Cerulean Dye", "search results are sorted")
XV.hits[1]:Click()
ok(IV.frame:IsShown() and not XV.frame:IsShown(), "clicking a search result opens the item view")
eq(ForeverMarketUISettings.item, "i:1", "last selected item is saved")
eq(IV.name:GetText(), "Cerulean Dye", "item name")
eq(IV.badge1.text:GetText(), "Trade good", "class badge")
eq(IV.badge2.text:GetText(), "Item level 25", "item level badge")
eq(IV.where:GetText(), "Typical price · US · PvP", "price caption")
eq(IV.counts.fill, IV.chart.plotW, "item chart: fill strips for 24 points")
eq(IV.counts.line, 2 * IV.chart.plotW, "item chart: typical and cheapest lines")
eq(IV.cards[2].value:GetText(), "33", "Auctions card")
eq(IV.cards[3].value:GetText(), "123", "Items for sale card")
eq(IV.regionRows[1].diff:GetText(), "cheapest", "cheapest region is marked")
ok(IV.regionRows[1].hl:IsShown() and not IV.regionRows[2].hl:IsShown(), "only the cheapest region is highlighted")
eq(IV.regionRows[4].diff:GetText(), "+50.0% vs cheapest", "region premium")
IV.regionRows[2]:Click()
eq(IV.cards[1].title:GetText(), "Cheapest now · EU", "clicking a region row shows that region's cheapest")
ok(IV.similarRows[1]:IsShown() and not IV.similarRows[2]:IsShown(), "copes with one similar item")
IV.add:Click()
eq(IV.add.text:GetText(), "- Remove from chart", "add to chart toggles")
IV.similarRows[1]:Click()
eq(IV.name:GetText(), "Crimson Dye", "clicking a similar row opens that item")
ok(IV.noRegion:IsShown(), "item without regions says so")
ns.ShowItem("i:3")
ok(IV.counts.line == 0 and IV.chart.none:IsShown(), "item with an empty series shows No data")
ns.ShowIndex()
eq(XV.counts.line, 3 * XV.chart.plotW, "charted item joins the index chart")
ForeverMarketUIFrame:GetScript("OnDragStop")(ForeverMarketUIFrame)
eq(ForeverMarketUISettings.pos[1], "CENTER", "position is saved on drag stop")

print(("smoke: %d checks passed"):format(checks))
