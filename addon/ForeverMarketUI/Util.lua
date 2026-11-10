-- Theme, formatting and the few widget helpers every view shares.
local ADDON, ns = ...
local U = {}
ns.U = U
local floor, min, max = math.floor, math.min, math.max

local function hex(h, a)
	return { tonumber(h:sub(2, 3), 16) / 255, tonumber(h:sub(4, 5), 16) / 255, tonumber(h:sub(6, 7), 16) / 255, a or 1 }
end

-- Theme: retune the whole window here.
local C = {
	bg = hex("#141414", 0.95),
	border = hex("#c8a84b"),
	heading = hex("#d8b96a"),
	body = hex("#d9d9d9"),
	green = hex("#4caf50"),
	white = hex("#ffffff"),
	amber = hex("#e69f3c"),
	red = hex("#e05a4f"),
	dim = hex("#8a8a8a"),
	panel = hex("#1e1e1e", 0.9),
	header = hex("#16301a", 0.95),
	highlight = hex("#c8a84b", 0.18),
	close = hex("#b3261e"),
	solid = hex("#141414", 1),
}
C.lines = { C.green, C.white, C.heading, hex("#5aa9e6"), hex("#e69f3c"), hex("#b07fe0"), hex("#4fd1c5"), hex("#e07fb0") }
ns.C = C

ns.REALM = "PvP" -- the export carries region and house id but no realm type; SPEC fixes this project to PvP-Horde
ns.RANGES = { { "6H", 6 * 3600 }, { "1D", 86400 }, { "1W", 7 * 86400 }, { "ALL" } }
ns.range = 2

-- formatting ---------------------------------------------------------------------------------

local UNIT = { "g", "s", "c" }
local COIN = {
	"|TInterface\\MoneyFrame\\UI-GoldIcon:12:12:1:0|t",
	"|TInterface\\MoneyFrame\\UI-SilverIcon:12:12:1:0|t",
	"|TInterface\\MoneyFrame\\UI-CopperIcon:12:12:1:0|t",
}

-- 381800 -> "38g 18s", 7500 -> "75s", 29 -> "29c": the two largest units, zero second unit dropped.
function U.Money(copper, icons)
	if type(copper) ~= "number" then return "-" end
	copper = floor(copper + 0.5)
	local v = { floor(copper / 10000), floor(copper / 100) % 100, copper % 100 }
	local first = v[1] > 0 and 1 or v[2] > 0 and 2 or 3
	local out = {}
	for i = first, min(first + 1, 3) do
		if i == first or v[i] > 0 then out[#out + 1] = v[i] .. (icons and COIN[i] or UNIT[i]) end
	end
	return table.concat(out, " ")
end

-- (last/first - 1) * 100 rounded to one decimal; nil when it cannot be computed.
function U.Pct(last, first)
	if type(last) ~= "number" or type(first) ~= "number" or first == 0 then return nil end
	return floor((last / first - 1) * 1000 + 0.5) / 10
end

function U.PctText(p)
	if not p then return "-", C.dim end
	return string.format("%+.1f%%", p), p > 0 and C.green or p < 0 and C.red or C.body
end

function U.Dur(seconds)
	if type(seconds) ~= "number" then return "?" end
	local m = math.floor(seconds / 60)
	if m < 1 then return "<1m" end
	if m < 60 then return m .. "m" end
	local h = math.floor(m / 60)
	return h .. "h" .. (m % 60 > 0 and string.format("%02d", m % 60) or "")
end


function U.Num(v)
	return type(v) == "number" and tostring(v) or "-"
end

-- series helpers -----------------------------------------------------------------------------

-- Points inside the selected range, anchored on the newest point so stale exports still draw.
function U.Visible(series)
	local out, newest = {}, nil
	if type(series) ~= "table" then return out end
	for _, p in ipairs(series) do
		if type(p) == "table" and type(p.t) == "number" then newest = max(newest or p.t, p.t) end
	end
	local span = ns.RANGES[ns.range][2]
	for _, p in ipairs(series) do
		if type(p) == "table" and type(p.t) == "number" and (not span or p.t >= newest - span) then out[#out + 1] = p end
	end
	return out
end

-- {t, v} list for one field; asPct turns values into % change from the first one.
function U.Points(series, field, asPct)
	local out, first = {}, nil
	for _, p in ipairs(series) do
		local v = p[field]
		if type(v) == "number" then
			first = first or v
			if not asPct then
				out[#out + 1] = { t = p.t, v = v }
			elseif first ~= 0 then
				out[#out + 1] = { t = p.t, v = (v / first - 1) * 100 }
			end
		end
	end
	return out
end

function U.Last(series, field)
	if type(series) ~= "table" then return nil end
	for i = #series, 1, -1 do
		local v = type(series[i]) == "table" and series[i][field]
		if type(v) == "number" then return v end
	end
end

-- widgets ------------------------------------------------------------------------------------

function U.Shown(obj, shown)
	if shown then obj:Show() else obj:Hide() end
end

function U.Color(tex, c, a)
	tex:SetColorTexture(c[1], c[2], c[3], a or c[4])
end

function U.Tex(parent, layer, c, a)
	local t = parent:CreateTexture(nil, layer or "BACKGROUND")
	if c then U.Color(t, c, a) end
	return t
end

local EDGES = { { "TOPLEFT", "TOPRIGHT" }, { "BOTTOMLEFT", "BOTTOMRIGHT" }, { "TOPLEFT", "BOTTOMLEFT", true }, { "TOPRIGHT", "BOTTOMRIGHT", true } }

-- Flat fill plus a 1 px border drawn from plain textures (no backdrop template needed).
function U.Box(f, bg, border)
	if bg then U.Tex(f, "BACKGROUND", bg):SetAllPoints(f) end
	if not border then return end
	for _, e in ipairs(EDGES) do
		local t = U.Tex(f, "BORDER", border)
		t:SetPoint(e[1])
		t:SetPoint(e[2])
		if e[3] then t:SetWidth(1) else t:SetHeight(1) end
	end
end

function U.Panel(parent, w, h, bg, border)
	local f = CreateFrame("Frame", nil, parent)
	f:SetSize(w, h)
	U.Box(f, bg, border)
	return f
end

function U.Text(parent, size, c, justify, width)
	local fs = parent:CreateFontString(nil, "OVERLAY")
	fs:SetFont(STANDARD_TEXT_FONT, size, "")
	fs:SetTextColor(c[1], c[2], c[3])
	fs:SetJustifyH(justify or "LEFT")
	if width then
		fs:SetWidth(width)
		fs:SetWordWrap(false)
	end
	return fs
end

-- With a label: bordered gold button. Without: a bare clickable row the caller fills in.
function U.Button(parent, w, h, label, onClick)
	local b = CreateFrame("Button", nil, parent)
	b:SetSize(w, h)
	if label then
		U.Box(b, C.panel, C.border)
		b.text = U.Text(b, 11, C.heading, "CENTER", w - 6)
		b.text:SetPoint("CENTER")
		b.text:SetText(label)
	end
	b.hl = U.Tex(b, "ARTWORK", C.highlight)
	b.hl:SetAllPoints(b)
	b.hl:Hide()
	b:SetScript("OnClick", onClick)
	return b
end

function U.RangeButtons(parent, onChange)
	local f = CreateFrame("Frame", nil, parent)
	f:SetSize(#ns.RANGES * 38 - 4, 18)
	f.buttons = {}
	for i, r in ipairs(ns.RANGES) do
		local b = U.Button(f, 34, 18, r[1], function()
			ns.range = i
			onChange()
		end)
		b:SetPoint("LEFT", (i - 1) * 38, 0)
		f.buttons[i] = b
	end
	function f.Refresh()
		for i, b in ipairs(f.buttons) do U.Shown(b.hl, i == ns.range) end
	end
	return f
end

function U.Icon(key)
	local id = tonumber(tostring(key):match("%d+"))
	local get = C_Item and C_Item.GetItemIconByID or GetItemIcon
	return id and get and get(id) or "Interface\\Icons\\INV_Misc_QuestionMark"
end
