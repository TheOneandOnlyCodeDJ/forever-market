-- Item view: header, four stat cards, price history, estimated sales, similar items.
local ADDON, ns = ...
local U, C, Charts = ns.U, ns.C, ns.Charts
local abs = math.abs
local V = {}
ns.ItemView = V

local CLASS = { [0] = "Consumable", [2] = "Weapon", [4] = "Armour", [7] = "Trade good", [9] = "Recipe" }
local REGIONS = { "us", "eu", "kr", "tw" }
local CARDS = { "Cheapest now", "Auctions", "Items for sale", "Vendor pays" }
local FOOTER = "Compared as % change from the start of the range"

-- Best current price we know for an item: typical, else cheapest, else the home-region listing.
function ns.Price(item)
	local r = type(item.regions) == "table" and item.regions[ns.Data().region or "us"]
	return U.Last(item.series, "typical") or U.Last(item.series, "cheapest") or (type(r) == "number" and r or nil)
end

-- Same class and subclass, nearest price first; may return fewer than four (or none).
function V.Similar(key)
	local items, out = ns.Items(), {}
	local me = items[key]
	if type(me) ~= "table" or me.c == nil then return out end
	local mine = ns.Price(me)
	for k, it in pairs(items) do
		if k ~= key and type(it) == "table" and it.c == me.c and it.s == me.s then
			local p = ns.Price(it)
			if p then out[#out + 1] = { key = k, item = it, price = p, d = mine and abs(p - mine) or 0 } end
		end
	end
	table.sort(out, function(a, b)
		if a.d ~= b.d then return a.d < b.d end
		return a.key < b.key
	end)
	for i = #out, 5, -1 do out[i] = nil end
	return out
end

local function badge(parent, w)
	local f = U.Panel(parent, w, 18, C.panel, C.border)
	f.text = U.Text(f, 10, C.body, "CENTER", w - 6)
	f.text:SetPoint("CENTER")
	return f
end

function V.Build(parent)
	local f = CreateFrame("Frame", nil, parent)
	f:SetAllPoints(parent)
	V.frame = f

	local head = U.Panel(f, 796, 92, C.header, C.border)
	head:SetPoint("TOPLEFT")
	local iconBox = U.Panel(head, 50, 50, nil, C.border)
	iconBox:SetPoint("LEFT", 12, 0)
	V.icon = iconBox:CreateTexture(nil, "ARTWORK")
	V.icon:SetSize(48, 48)
	V.icon:SetPoint("CENTER")
	V.name = U.Text(head, 18, C.green, "LEFT", 430)
	V.name:SetPoint("TOPLEFT", iconBox, "TOPRIGHT", 12, -2)
	V.badge1 = badge(head, 96)
	V.badge1:SetPoint("BOTTOMLEFT", iconBox, "BOTTOMRIGHT", 12, 2)
	V.badge2 = badge(head, 110)
	V.badge2:SetPoint("LEFT", V.badge1, "RIGHT", 6, 0)
	V.where = U.Text(head, 10, C.heading, "RIGHT")
	V.where:SetPoint("TOPRIGHT", -12, -10)
	V.price = U.Text(head, 20, C.white, "RIGHT")
	V.price:SetPoint("TOPRIGHT", -12, -26)
	V.add = U.Button(head, 130, 22, "+ Add to chart", function()
		ns.IndexView.ToggleCharted(V.key)
		V.Refresh()
	end)
	V.add:SetPoint("BOTTOMRIGHT", -12, 10)

	V.cards = {}
	for i, title in ipairs(CARDS) do
		local card = U.Panel(f, 193, 50, C.panel, C.border)
		card:SetPoint("TOPLEFT", (i - 1) * 201, -100)
		card.title = U.Text(card, 10, C.heading)
		card.title:SetPoint("TOPLEFT", 10, -8)
		card.title:SetText(title)
		card.value = U.Text(card, 14, C.body)
		card.value:SetPoint("BOTTOMLEFT", 10, 9)
		V.cards[i] = card
	end

	local left = U.Panel(f, 526, 370, C.panel, C.border)
	left:SetPoint("TOPLEFT", 0, -158)
	local h1 = U.Text(left, 11, C.heading)
	h1:SetPoint("TOPLEFT", 10, -10)
	h1:SetText("PRICE HISTORY")
	V.ranges = U.RangeButtons(left, function() ns.Refresh() end)
	V.ranges:SetPoint("TOPRIGHT", -10, -7)
	local x = 10
	for _, l in ipairs({ { "Typical price", C.green }, { "Cheapest listing", C.white } }) do
		local sw = U.Tex(left, "ARTWORK", l[2], 1)
		sw:SetSize(10, 10)
		sw:SetPoint("TOPLEFT", x, -34)
		local fs = U.Text(left, 10, C.body)
		fs:SetPoint("LEFT", sw, "RIGHT", 5, 0)
		fs:SetText(l[1])
		x = x + 110
	end
	V.chart = Charts.New(left, 506, 214, function(v) return U.Money(v, true) end)
	V.chart.frame:SetPoint("TOPLEFT", 10, -52)
	local h2 = U.Text(left, 10, C.dim)
	h2:SetPoint("TOPLEFT", 10, -272)
	h2:SetText("Items for sale each hour")
	V.bars = Charts.Bars(left, V.chart.plotW, 44)
	V.bars.frame:SetPoint("TOPLEFT", 10, -288)
	V.footer = U.Text(left, 10, C.dim)
	V.footer:SetPoint("BOTTOMLEFT", 10, 10)
	V.footPct = U.Text(left, 10, C.body)
	V.footPct:SetPoint("LEFT", V.footer, "RIGHT", 4, 0)

	local right = U.Panel(f, 262, 370, C.panel, C.border)
	right:SetPoint("TOPRIGHT", 0, -158)
	local h3 = U.Text(right, 11, C.heading)
	h3:SetPoint("TOPLEFT", 10, -10)
	h3:SetText("ESTIMATED SALES")
	V.noRegion = U.Text(right, 10, C.dim)
	V.noRegion:SetPoint("TOPLEFT", 10, -34)
	V.noRegion:SetText("No sales measured yet (first hour of tracking)")
	V.regionRows = {}
	for i = 1, 4 do
		local r = U.Button(right, 242, 22, nil, function() end)
		r:SetPoint("TOPLEFT", 10, -30 - (i - 1) * 24)
		r.name = U.Text(r, 11, C.heading)
		r.name:SetPoint("LEFT", 4, 0)
		r.diff = U.Text(r, 10, C.body)
		r.diff:SetPoint("LEFT", 36, 0)
		r.price = U.Text(r, 11, C.body, "RIGHT")
		r.price:SetPoint("RIGHT", -4, 0)
		V.regionRows[i] = r
	end
	local h4 = U.Text(right, 11, C.heading)
	h4:SetPoint("TOPLEFT", 10, -140)
	h4:SetText("SIMILAR ON THE AUCTION HOUSE")
	V.noSimilar = U.Text(right, 10, C.dim)
	V.noSimilar:SetPoint("TOPLEFT", 10, -164)
	V.noSimilar:SetText("No similar items in the export")
	V.similarRows = {}
	for i = 1, 4 do
		local r = U.Button(right, 242, 30, nil, function(self) ns.ShowItem(self.key) end)
		r:SetPoint("TOPLEFT", 10, -160 - (i - 1) * 34)
		r.icon = r:CreateTexture(nil, "ARTWORK")
		r.icon:SetSize(24, 24)
		r.icon:SetPoint("LEFT", 3, 0)
		r.name = U.Text(r, 11, C.body, "LEFT", 130)
		r.name:SetPoint("LEFT", 34, 0)
		r.price = U.Text(r, 11, C.body, "RIGHT")
		r.price:SetPoint("RIGHT", -4, 0)
		V.similarRows[i] = r
	end
end

function V.Refresh()
	local d, item = ns.Data(), ns.Items()[V.key]
	if type(item) ~= "table" then return end
	local series = U.Visible(item.series)

	V.icon:SetTexture(U.Icon(V.key))
	V.name:SetText(item.n or V.key)
	U.Shown(V.badge1, item.c ~= nil)
	V.badge1.text:SetText(CLASS[item.c] or "Other")
	U.Shown(V.badge2, item.il ~= nil)
	V.badge2.text:SetText("Item level " .. tostring(item.il))
	local age = d.generated_ts and (time() - d.generated_ts) or nil
	local due = d.next_update and math.max(0, d.next_update - time()) or nil
	local stamp = age and string.format(" · updated %s ago · next ~%s", U.Dur(age), U.Dur(due)) or ""
	if not age then stamp = "" end
	V.where:SetText("Typical price · " .. tostring(d.region or "?"):upper() .. " · " .. ns.REALM .. stamp)
	V.price:SetText(U.Money(U.Last(item.series, "typical"), true))
	V.add.text:SetText(ns.IndexView.IsCharted(V.key) and "- Remove from chart" or "+ Add to chart")

	V.cards[1].title:SetText(CARDS[1])
	V.cards[1].value:SetText(U.Money(U.Last(item.series, "cheapest"), true))
	V.cards[2].value:SetText(U.Num(U.Last(item.series, "auctions")))
	V.cards[3].value:SetText(U.Num(U.Last(item.series, "qty")))
	V.cards[4].value:SetText(U.Money(item.vendor, true))

	local typical = U.Points(series, "typical")
	V.counts = V.chart:Draw({
		{ pts = typical, color = C.green, fill = true },
		{ pts = U.Points(series, "cheapest"), color = C.white },
	})
	V.bars:Draw(U.Points(series, "qty"))
	local text, color = U.PctText(#typical > 0 and U.Pct(typical[#typical].v, typical[1].v) or nil)
	V.footer:SetText(FOOTER .. ":")
	V.footPct:SetText(text)
	V.footPct:SetTextColor(color[1], color[2], color[3])
	V.ranges.Refresh()

	-- estimated sales: vanished auctions that could not have expired, plus his own TSM sales
	local sold = type(item.sold) == "table" and item.sold or nil
	local mine = type(item.my) == "table" and item.my or nil
	local lines = {
		{ "Sold (estimated)", sold and (U.Num(sold.q) .. " units") or "-" },
		{ "Auctions gone", sold and U.Num(sold.n) or "-" },
		{ "Copper moved (est.)", sold and U.Money(sold.t, true) or "-" },
		{ "Your sales", mine and (U.Num(mine.n) .. " @ " .. U.Money(mine.u, true)) or "-" },
	}
	local n = 0
	for i, line in ipairs(lines) do
		local row = V.regionRows[i]
		row.name:SetText(line[1])
		row.diff:SetText("")
		row.price:SetText(line[2])
		row:Show()
		n = n + 1
	end
	for i = n + 1, #V.regionRows do V.regionRows[i]:Hide() end
	U.Shown(V.noRegion, sold == nil and mine == nil)

	local similar = V.Similar(V.key)
	for i, row in ipairs(V.similarRows) do
		local s = similar[i]
		U.Shown(row, s)
		if s then
			row.key = s.key
			row.icon:SetTexture(U.Icon(s.key))
			row.name:SetText(s.item.n or s.key)
			row.price:SetText(U.Money(s.price, true))
		end
	end
	U.Shown(V.noSimilar, #similar == 0)
end
