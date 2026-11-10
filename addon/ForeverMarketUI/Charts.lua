-- Line/area charts built only from Texture strips: one texture per pixel column per series.
local ADDON, ns = ...
local U, C = ns.U, ns.C
local floor, min, max, abs = math.floor, math.min, math.max, math.abs
local Charts = {}
ns.Charts = Charts

local AXIS_W, AXIS_H = 64, 14
local LAYER = { fill = "BACKGROUND", line = "ARTWORK", dot = "OVERLAY" }

local function release(self)
	for pool in pairs(LAYER) do
		for i = 1, self.used[pool] do self[pool][i]:Hide() end
		self.used[pool] = 0
	end
end

local function acquire(self, pool, x, y, h)
	local n = self.used[pool] + 1
	self.used[pool] = n
	local t = self[pool][n]
	if not t then
		t = self.plot:CreateTexture(nil, LAYER[pool])
		t:SetWidth(1)
		self[pool][n] = t
	end
	t:ClearAllPoints()
	t:SetPoint("BOTTOMLEFT", x, y)
	t:SetHeight(max(1, h))
	t:Show()
	return t
end

-- Green column fading towards the axis; flat tint where the client has no gradient call.
local function gradient(t, c)
	if t.SetGradient and CreateColor then
		t:SetColorTexture(1, 1, 1, 1)
		t:SetGradient("VERTICAL", CreateColor(c[1], c[2], c[3], 0.03), CreateColor(c[1], c[2], c[3], 0.4))
	elseif t.SetGradientAlpha then
		t:SetColorTexture(1, 1, 1, 1)
		t:SetGradientAlpha("VERTICAL", c[1], c[2], c[3], 0.03, c[1], c[2], c[3], 0.4)
	else
		U.Color(t, c, 0.2)
	end
end

-- Value at every pixel column, linearly interpolated in time. One point is a flat line.
local function columns(pts, t0, t1, w)
	local ys, n, j = {}, #pts, 1
	for x = 0, w - 1 do
		if n == 1 or t1 == t0 then
			ys[x] = pts[n].v
		else
			local t = t0 + (t1 - t0) * x / (w - 1)
			if t >= pts[1].t and t <= pts[n].t then
				while j < n and pts[j + 1].t <= t do j = j + 1 end
				local a, b = pts[j], pts[j + 1]
				ys[x] = b and b.t > a.t and a.v + (b.v - a.v) * (t - a.t) / (b.t - a.t) or a.v
			end
		end
	end
	return ys
end

local Chart = {}
Chart.__index = Chart

function Charts.New(parent, w, h, fmtY)
	local self = setmetatable({ fmtY = fmtY, fill = {}, line = {}, dot = {}, used = { fill = 0, line = 0, dot = 0 }, yl = {}, xl = {}, dots = {} }, Chart)
	self.plotW, self.plotH = w - AXIS_W, h - AXIS_H
	self.frame = CreateFrame("Frame", nil, parent)
	self.frame:SetSize(w, h)
	self.plot = CreateFrame("Frame", nil, self.frame)
	self.plot:SetSize(self.plotW, self.plotH)
	self.plot:SetPoint("TOPLEFT")
	for i = 1, 4 do
		local y = -(i - 1) * (self.plotH - 1) / 3
		local grid = U.Tex(self.plot, "BORDER", C.white, 0.07)
		grid:SetHeight(1)
		grid:SetPoint("TOPLEFT", 0, y)
		grid:SetPoint("TOPRIGHT", 0, y)
		local fs = U.Text(self.frame, 10, C.heading, "RIGHT", AXIS_W - 4)
		fs:SetPoint("RIGHT", self.frame, "TOPRIGHT", 0, min(-5, max(y, 5 - self.plotH)))
		self.yl[i] = fs
	end
	for i, a in ipairs({ { "TOPLEFT", "BOTTOMLEFT", "LEFT" }, { "TOP", "BOTTOM", "CENTER" }, { "TOPRIGHT", "BOTTOMRIGHT", "RIGHT" } }) do
		local fs = U.Text(self.frame, 10, C.dim, a[3])
		fs:SetPoint(a[1], self.plot, a[2], 0, -2)
		self.xl[i] = fs
	end
	self.none = U.Text(self.plot, 12, C.dim, "CENTER")
	self.none:SetPoint("CENTER")
	self.none:SetText("No data")
	self:_Hover()
	return self
end

-- Cursor readout: a vertical guide and the values of the nearest point of every series.
function Chart:_Hover()
	if not GetCursorPosition then return end
	self.guide = U.Tex(self.plot, "OVERLAY", C.white, 0.35)
	self.guide:SetWidth(1)
	self.guide:SetPoint("BOTTOMLEFT", 0, 0)
	self.guide:SetPoint("TOP", self.plot, "TOP", 0, 0)
	self.guide:Hide()
	self.tip = CreateFrame("Frame", nil, self.frame)
	self.tip:SetSize(110, 20)
	self.tip:SetFrameStrata("TOOLTIP")
	local bg = self.tip:CreateTexture(nil, "BACKGROUND")
	bg:SetAllPoints()
	U.Color(bg, C.panel, 0.95)
	self.tipText = U.Text(self.tip, 11, C.body, "LEFT", 104)
	self.tipText:SetPoint("LEFT", 4, 0)
	self.tip:Hide()
	self.plot:EnableMouse(true)
	self.plot:SetScript("OnUpdate", function()
		local t0, t1 = self.hoverT0, self.hoverT1
		if not t0 or t1 == t0 then return end
		local sx, sy = GetCursorPosition()
		local scale = self.plot:GetEffectiveScale()
		sx, sy = sx / scale, sy / scale
		local left, bottom = self.plot:GetLeft(), self.plot:GetBottom()
		if not left then return end
		local x, y = sx - left, sy - bottom
		if x < 0 or x > self.plotW - 1 or y < 0 or y > self.plotH then
			if self.tip:IsShown() then self.tip:Hide() self.guide:Hide() end
			return
		end
		-- only a dot answers: the legend already says which line is which
		local best, bd = nil, 8
		for _, d in ipairs(self.dots or {}) do
			local dist = math.sqrt((d.x - x) ^ 2 + (d.y - y) ^ 2)
			if dist <= bd then best, bd = d, dist end
		end
		if not best then
			if self.tip:IsShown() then self.tip:Hide() self.guide:Hide() end
			return
		end
		self.tipText:SetText(self.fmtY(best.v))
		self.tip:ClearAllPoints()
		self.tip:SetPoint("BOTTOMLEFT", self.frame, "BOTTOMLEFT",
			floor(min(best.x + 8, self.plotW - 150)), floor(min(best.y + 10, self.plotH)))
		self.tip:Show()
		self.guide:Hide()
	end)
end

-- series: list of { pts = { {t=, v=}, ... }, color = {r,g,b}, fill = bool, label = string }.
-- Returns the texture counts: fill strips and line strips (plotW each per drawn series).
function Chart:Draw(series)
	release(self)
	local t0, t1, lo, hi
	for _, s in ipairs(series) do
		for _, p in ipairs(s.pts) do
			t0, t1 = min(t0 or p.t, p.t), max(t1 or p.t, p.t)
			lo, hi = min(lo or p.v, p.v), max(hi or p.v, p.v)
		end
	end
	if self.tip then self.tip:Hide() self.guide:Hide() end
	U.Shown(self.none, not lo)
	for _, fs in ipairs(self.yl) do U.Shown(fs, lo) end
	for _, fs in ipairs(self.xl) do U.Shown(fs, lo) end
	if not lo then return { fill = 0, line = 0 } end
	if hi == lo then -- flat: centre it instead of dividing by zero
		local pad = hi ~= 0 and abs(hi) * 0.05 or 1
		lo, hi = lo - pad, hi + pad
	end
	self.hoverT0, self.hoverT1 = t0, t1
	self.t0 = series
	local w, scale = self.plotW, (self.plotH - 1) / (hi - lo)
	for _, s in ipairs(series) do
		if #s.pts > 0 then
			local ys = columns(s.pts, t0, t1, w)
			for x = 0, w - 1 do
				if ys[x] then
					local y = (ys[x] - lo) * scale
					local y2 = ys[x + 1] and (ys[x + 1] - lo) * scale or y
					if s.fill then gradient(acquire(self, "fill", x, 0, y), s.color) end
					U.Color(acquire(self, "line", x, min(y, y2), abs(y2 - y)), s.color, 1)
				end
			end
		end
	end
	-- a dot at each measured point so the samples are visible, not just the line between them
	self.dots = {}
	for _, s in ipairs(series) do
		local lastX
		for _, p in ipairs(s.pts) do
			local px = t1 > t0 and floor((p.t - t0) / (t1 - t0) * (w - 1) + 0.5) or 0
			if not lastX or px - lastX >= 5 or p == s.pts[#s.pts] then
				lastX = px
				local py = (p.v - lo) * scale
				local t = acquire(self, "dot", px - 1, max(0, py - 1), 3)
				t:SetWidth(3)
				U.Color(t, s.color, 1)
				self.dots[#self.dots + 1] = { x = px, y = py, v = p.v }
			end
		end
	end
	for i, fs in ipairs(self.yl) do fs:SetText(self.fmtY(hi - (hi - lo) * (i - 1) / 3)) end
	local fmt = t1 - t0 > 2 * 86400 and "%d %b" or "%H:%M"
	self.xl[1]:SetText(t1 > t0 and date(fmt, t0) or "")
	self.xl[2]:SetText(date(t1 > t0 and fmt or "%d %b %H:%M", (t0 + t1) / 2))
	self.xl[3]:SetText(t1 > t0 and date(fmt, t1) or "")
	return { fill = self.used.fill, line = self.used.line }
end

-- Bar strip: one texture per point, scaled to the tallest. Returns the bar count.
function Charts.Bars(parent, w, h)
	local self = { line = {}, fill = {}, dot = {}, used = { fill = 0, line = 0, dot = 0 } }
	self.plot = CreateFrame("Frame", nil, parent)
	self.plot:SetSize(w, h)
	self.frame = self.plot
	function self:Draw(pts)
		release(self)
		local top = 0
		for _, p in ipairs(pts) do top = max(top, p.v) end
		if top <= 0 then return 0 end
		local bw = w / #pts
		for i, p in ipairs(pts) do
			local t = acquire(self, "line", floor((i - 1) * bw), 0, p.v / top * h)
			t:SetWidth(max(1, floor(bw) - 1))
			U.Color(t, C.heading, 0.6)
		end
		return #pts
	end
	return self
end
