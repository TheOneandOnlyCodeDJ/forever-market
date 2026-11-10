-- Index view: sector list with % change, multi-line chart, item search.
local ADDON, ns = ...
local U, C, Charts = ns.U, ns.C, ns.Charts
local V = {}
ns.IndexView = V

local SECTORS = { "Forever 100", "Trade goods", "Consumables", "Armour", "Weapons", "Recipes", "Other" }
local MAX_CHARTED, MAX_HITS = 8, 8
V.selected = { ["Forever 100"] = true }
V.charted = {} -- item keys added with "+ Add to chart"; this session only

function V.IsCharted(key)
	for i, k in ipairs(V.charted) do
		if k == key then return i end
	end
end

function V.ToggleCharted(key)
	local i = V.IsCharted(key)
	if i then
		table.remove(V.charted, i)
	elseif #V.charted < MAX_CHARTED then
		V.charted[#V.charted + 1] = key
	else
		print("ForeverMarket: the chart already holds " .. MAX_CHARTED .. " items, remove one first")
	end
end

local function rowClick(self)
	local e = self.entry
	if e.key then return ns.ShowItem(e.key) end
	if IsShiftKeyDown() then
		V.selected[e.label] = not V.selected[e.label] or nil
	else
		V.selected = { [e.label] = true }
	end
	V.Refresh()
end

local function row(i)
	local r = V.rows[i]
	if r then return r end
	r = U.Button(V.list, 234, 22, nil, rowClick)
	r:SetPoint("TOPLEFT", 8, -30 - (i - 1) * 24)
	r.swatch = U.Tex(r, "OVERLAY")
	r.swatch:SetSize(10, 10)
	r.swatch:SetPoint("LEFT", 4, 0)
	r.name = U.Text(r, 11, C.body, "LEFT", 150)
	r.name:SetPoint("LEFT", 20, 0)
	r.pct = U.Text(r, 11, C.body, "RIGHT")
	r.pct:SetPoint("RIGHT", -4, 0)
	V.rows[i] = r
	return r
end

-- Fills the dropdown under the search box; returns how many rows it shows.
function V.Search(text)
	local q, hits = tostring(text or ""):lower(), {}
	if #q >= 2 then
		for key, it in pairs(ns.Items()) do
			if type(it) == "table" and type(it.n) == "string" and it.n:lower():find(q, 1, true) then
				hits[#hits + 1] = { key = key, n = it.n }
			end
		end
	end
	table.sort(hits, function(a, b)
		if a.n ~= b.n then return a.n < b.n end
		return a.key < b.key
	end)
	for i, r in ipairs(V.hits) do
		local h = hits[i]
		U.Shown(r, h)
		if h then
			r.key = h.key
			r.name:SetText(h.n)
		end
	end
	local shown = math.min(#hits, MAX_HITS)
	V.results:SetHeight(shown * 20 + 4)
	U.Shown(V.results, shown > 0)
	return shown
end

function V.Build(parent)
	local f = CreateFrame("Frame", nil, parent)
	f:SetAllPoints(parent)
	V.frame = f

	local title = U.Text(f, 12, C.heading)
	title:SetPoint("TOPLEFT", 0, -4)
	title:SetText("MARKET INDEX")
	V.ranges = U.RangeButtons(f, function() ns.Refresh() end)
	V.ranges:SetPoint("TOPRIGHT")

	local box = CreateFrame("EditBox", nil, f)
	box:SetSize(220, 20)
	box:SetPoint("RIGHT", V.ranges, "LEFT", -12, 0)
	U.Box(box, C.panel, C.border)
	box:SetFont(STANDARD_TEXT_FONT, 11, "")
	box:SetTextColor(C.body[1], C.body[2], C.body[3])
	box:SetTextInsets(6, 6, 0, 0)
	box:SetAutoFocus(false)
	box:SetMaxLetters(40)
	local hint = U.Text(box, 11, C.dim)
	hint:SetPoint("LEFT", 6, 0)
	hint:SetText("Search items")
	box:SetScript("OnTextChanged", function(self)
		local text = self:GetText() or ""
		U.Shown(hint, text == "")
		V.Search(text)
	end)
	box:SetScript("OnEscapePressed", function(self)
		self:SetText("")
		self:ClearFocus()
	end)
	box:SetScript("OnEnterPressed", function(self)
		local first = V.hits[1]
		if V.results:IsShown() and first.key then first:Click() end
	end)
	V.box = box

	V.results = U.Panel(f, 220, 4, C.solid, C.border)
	V.results:SetPoint("TOPLEFT", box, "BOTTOMLEFT", 0, -2)
	V.results:SetFrameStrata("DIALOG") -- above the panels it overlaps
	V.results:Hide()
	V.hits = {}
	for i = 1, MAX_HITS do
		local r = U.Button(V.results, 216, 20, nil, function(self)
			box:SetText("")
			box:ClearFocus()
			ns.ShowItem(self.key)
		end)
		r:SetPoint("TOPLEFT", 2, -2 - (i - 1) * 20)
		r.name = U.Text(r, 11, C.body, "LEFT", 206)
		r.name:SetPoint("LEFT", 5, 0)
		V.hits[i] = r
	end

	V.list = U.Panel(f, 250, 494, C.panel, C.border)
	V.list:SetPoint("TOPLEFT", 0, -30)
	local h1 = U.Text(V.list, 11, C.heading)
	h1:SetPoint("TOPLEFT", 10, -10)
	h1:SetText("SECTORS")
	V.rows = {}

	local panel = U.Panel(f, 538, 494, C.panel, C.border)
	panel:SetPoint("TOPRIGHT", 0, -30)
	local h2 = U.Text(panel, 11, C.heading)
	h2:SetPoint("TOPLEFT", 10, -10)
	h2:SetText("INDEX HISTORY")
	V.chart = Charts.New(panel, 518, 420, function(v) return string.format("%+.1f%%", v) end)
	V.chart.frame:SetPoint("TOPLEFT", 10, -34)
	local foot = U.Text(panel, 10, C.dim)
	foot:SetPoint("BOTTOMLEFT", 10, 10)
	foot:SetText("Compared as % change from the start of the range")
end

function V.Refresh()
	local indices, items = ns.Indices(), ns.Items()
	local entries = {}
	for _, name in ipairs(SECTORS) do
		entries[#entries + 1] = { label = name, field = "v", series = indices[name], drawn = V.selected[name] }
	end
	for _, key in ipairs(V.charted) do
		local it = items[key]
		if type(it) == "table" then
			local field = U.Last(it.series, "typical") and "typical" or "cheapest"
			entries[#entries + 1] = { label = it.n or key, key = key, field = field, series = it.series, drawn = true }
		end
	end
	local lines = {}
	for i, e in ipairs(entries) do
		local pts = U.Points(U.Visible(e.series), e.field, true) -- already % change from the range start
		local r = row(i)
		r.entry = e
		r.name:SetText(e.label)
		local last = pts[#pts]
		local text, color = U.PctText(last and math.floor(last.v * 10 + 0.5) / 10 or nil)
		r.pct:SetText(text)
		r.pct:SetTextColor(color[1], color[2], color[3])
		U.Shown(r.hl, e.drawn)
		local c = C.dim
		if e.drawn then
			c = C.lines[#lines % #C.lines + 1]
			lines[#lines + 1] = { pts = pts, color = c, label = e.label }
		end
		U.Color(r.swatch, c, 1)
		r:Show()
	end
	for i = #entries + 1, #V.rows do V.rows[i]:Hide() end
	V.counts = V.chart:Draw(lines)
	V.ranges.Refresh()
end
