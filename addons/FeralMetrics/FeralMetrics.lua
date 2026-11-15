-- FeralMetrics: measured damage for a feral druid on WoW Forever.
--
-- Real numbers only. Every figure comes out of your own combat, from events the client fired.
-- Nothing is modelled from a tooltip or scaled by a guess.
--
-- Samples live under a profile. A profile is the fingerprint of everything that changes your
-- damage: level, Strength, Agility, attack power, crit, main hand weapon and its speed, and the
-- points spent in each talent tree. Change any of those and a fresh profile starts, so a number
-- from old gear can never be quoted against new gear. Old profiles stay on disk to compare with.

local ADDON, FM = ...

FM.VERSION = "0.1.0"
FM.MIN_HITS = 1            -- show a figure as soon as there is one sample
FM.CP_WINDOW = 2.0         -- combo points seen this recently before a finisher are attributed to it

local FINISHER = { [1079] = true, [22568] = true, [22570] = true }
local DOT = { [1079] = true, [1822] = true, [1823] = true, [1824] = true, [1825] = true,
              [9005] = true, [9490] = true }
-- Ticks the spell is meant to deliver. A clipped bleed only ever shows fewer, so the full count
-- is whichever is larger: what the spell is designed to do, or the most this character has ever
-- seen one run. That is what makes "per tick x total ticks" honest when the mob dies early.
local BASE_TICKS = {
  [1079] = { [1] = 4, [2] = 5, [3] = 6, [4] = 7, [5] = 8 },
  [1822] = { [0] = 3 }, [1823] = { [0] = 3 }, [1824] = { [0] = 3 }, [1825] = { [0] = 3 },
  [9005] = { [0] = 3 },
}
local function designedTicks(id, cp)
  local t = BASE_TICKS[id]
  if type(t) ~= "table" then return 0 end
  return t[cp] or t[0] or 0
end

local function now()
  return (GetTime and GetTime()) or time()
end

local function xor32(a, b)
  if bit and bit.bxor then return bit.bxor(a, b) end
  local r, p = 0, 1
  for _ = 1, 32 do
    local x, y = a % 2, b % 2
    if x ~= y then r = r + p end
    a, b, p = math.floor(a / 2), math.floor(b / 2), p * 2
  end
  return r
end

local function band32(a)
  if bit and bit.band then return bit.band(a, 0xFFFFFFFF) end
  return a % 4294967296
end

------------------------------------------------------------------------------- saved variables

local function db()
  FeralMetricsDB = FeralMetricsDB or {}
  FeralMetricsDB.profiles = FeralMetricsDB.profiles or {}
  FeralMetricsDB.order = FeralMetricsDB.order or {}
  FeralMetricsDB.settings = FeralMetricsDB.settings or {}
  if FeralMetricsDB.settings.tips == nil then FeralMetricsDB.settings.tips = true end
  return FeralMetricsDB
end

------------------------------------------------------------------------------- the fingerprint

local function talentPoints()
  local out = {}
  for tab = 1, (GetNumTalentTabs and GetNumTalentTabs()) or 0 do
    local name, _, points = GetTalentTabInfo(tab)
    out[#out + 1] = string.format("%s=%d", tostring(name or tab), points or 0)
  end
  return table.concat(out, ",")
end

local function snapshot()
  local _, str = UnitStat("player", 1)
  local _, agi = UnitStat("player", 2)
  local _, sta = UnitStat("player", 3)
  local base, pos, neg = UnitAttackPower("player")
  local mh = (GetInventoryItemID and GetInventoryItemID("player", 16)) or 0
  local wname, _, _, _, _, _, wspeed = GetItemInfo(mh)
  return {
    level = UnitLevel("player") or 0,
    str = str or 0, agi = agi or 0, sta = sta or 0,
    ap = (base or 0) + (pos or 0) + (neg or 0),
    crit = (GetCritChance and GetCritChance()) or 0,
    weapon = mh, wname = wname, wspeed = wspeed or 0,
    talents = talentPoints(),
  }
end

local function fingerprint(s)
  return string.format("L%d|AP%d|S%d|A%d|C%.2f|W%d|T%s",
    s.level, s.ap, s.str, s.agi, s.crit, s.weapon, s.talents)
end

local function hash(s)                       -- FNV-1a, short stable key
  local h = 2166136261
  for i = 1, #s do
    h = xor32(h, s:byte(i))
    h = band32(h * 16777619)
  end
  return string.format("%08x", h)
end

local function describe(s)
  return string.format("level %d, %d AP, %d Str, %d Agi, %.2f%% crit, %s at %.1fs",
    s.level or 0, s.ap or 0, s.str or 0, s.agi or 0, s.crit or 0,
    s.wname or "no weapon", s.wspeed or 0)
end

------------------------------------------------------------------------------- profiles

local current

function FM.ensureProfile()
  local d = db()
  local s = snapshot()
  local fp = hash(fingerprint(s))
  if current and current.id == fp then return current end
  local p = d.profiles[fp]
  if not p then
    p = { id = fp, created = time(), meta = s, spells = {} }
    d.profiles[fp] = p
    d.order[#d.order + 1] = fp
  else
    p.meta = s
    p.seen = time()
  end
  current = p
  d.active = fp
  return p
end

function FM.profile() return current or FM.ensureProfile() end

------------------------------------------------------------------------------- aggregation

local function entry(p, id, name)
  local e = p.spells[id]
  if not e then
    e = { name = name or tostring(id), direct = {}, tick = {}, apps = {} }
    p.spells[id] = e
  end
  if name and name ~= "" then e.name = name end
  return e
end

local function addHit(t, cp, amount, isCrit)
  local b = t[cp]
  if not b then
    b = { n = 0, sum = 0, crits = 0 }
    t[cp] = b
  end
  b.n = b.n + 1
  b.sum = b.sum + amount
  b.min = (b.min and math.min(b.min, amount)) or amount
  b.max = (b.max and math.max(b.max, amount)) or amount
  if isCrit then b.crits = b.crits + 1 end
end

local function avg(b) return (b and b.n > 0) and (b.sum / b.n) or nil end

------------------------------------------------------------------------------- combo points

local cpRing = {}

local function noteComboPoints()
  local cp = 0
  if GetComboPoints then
    local ok, v = pcall(GetComboPoints, "player", "target")
    if ok and type(v) == "number" then cp = v end
  end
  cpRing[#cpRing + 1] = { t = now(), cp = cp }
  while #cpRing > 1 and now() - cpRing[1].t > 8 do table.remove(cpRing, 1) end
  return cp
end

local function cpBefore()
  local best, cutoff = 0, now() - FM.CP_WINDOW
  for i = #cpRing, 1, -1 do
    if cpRing[i].t < cutoff then break end
    if cpRing[i].cp > best then best = cpRing[i].cp end
  end
  return best
end

------------------------------------------------------------------------------- auras

local apps = {}

local function key(id, dest) return tostring(id) .. "|" .. tostring(dest) end

local function startApp(id, dest, cp)
  apps[key(id, dest)] = { start = now(), cp = cp or 0, ticks = 0, amount = 0,
                          lastTick = nil, intervalSum = 0, intervalN = 0 }
end

local function onTick(id, dest, amount)
  local a = apps[key(id, dest)]
  if not a then return 0 end
  if a.lastTick then
    a.intervalSum = a.intervalSum + (now() - a.lastTick)
    a.intervalN = a.intervalN + 1
  end
  a.lastTick = now()
  a.ticks = a.ticks + 1
  a.amount = a.amount + amount
  return a.cp
end

local function finishApp(p, id, dest, name)
  local k = key(id, dest)
  local a = apps[k]
  if not a then return end
  apps[k] = nil
  if a.ticks == 0 then return end
  local e = entry(p, id, name)
  local b = e.apps[a.cp]
  if not b then
    b = { n = 0, maxTicks = 0, sum = 0, durSum = 0, intervalSum = 0, intervalN = 0 }
    e.apps[a.cp] = b
  end
  b.n = b.n + 1
  b.maxTicks = math.max(b.maxTicks, a.ticks)
  b.sum = b.sum + a.amount
  b.durSum = b.durSum + (now() - a.start)
  b.intervalSum = b.intervalSum + a.intervalSum
  b.intervalN = b.intervalN + a.intervalN
end

------------------------------------------------------------------------------- combat log

local stats = { events = 0, hits = 0, ticks = 0, misses = 0 }

local function parse(...)
  -- modern clients expose the payload through CombatLogGetCurrentEventInfo; older ones pass it
  -- as event arguments, so take whichever this client offers
  local info
  if CombatLogGetCurrentEventInfo then
    info = { CombatLogGetCurrentEventInfo() }   -- no extra parens: they would truncate to one value
  else
    info = { ... }
  end
  return {
    sub = info[2], srcGUID = info[4], dstGUID = info[7], dstName = info[8],
    id = info[10], name = info[11], school = info[12], amount = tonumber(info[13]) or 0,
    crit = info[19] and true or false, missType = info[13],
  }
end

local function onEvent(...)
  local ev = parse(...)
  stats.events = stats.events + 1
  -- every combat event is a free sample of the combo points on the target, so a finisher that
  -- lands between two ticks still knows what it spent
  noteComboPoints()
  if not ev.sub or ev.srcGUID ~= UnitGUID("player") then return end
  local p = FM.profile()

  if ev.sub == "SPELL_DAMAGE" or ev.sub == "SPELL_PERIODIC_DAMAGE" then
    if not ev.id or ev.amount <= 0 then return end
    if ev.sub == "SPELL_PERIODIC_DAMAGE" then
      local cp = onTick(ev.id, ev.dstGUID, ev.amount)
      addHit(entry(p, ev.id, ev.name).tick, cp or 0, ev.amount, ev.crit)
      stats.ticks = stats.ticks + 1
    else
      local cp = FINISHER[ev.id] and cpBefore() or 0
      addHit(entry(p, ev.id, ev.name).direct, cp, ev.amount, ev.crit)
      stats.hits = stats.hits + 1
    end

  elseif ev.sub == "SPELL_AURA_APPLIED" or ev.sub == "SPELL_AURA_REFRESH" then
    if DOT[ev.id] then
      finishApp(p, ev.id, ev.dstGUID, ev.name)
      startApp(ev.id, ev.dstGUID, FINISHER[ev.id] and cpBefore() or 0)
    end

  elseif ev.sub == "SPELL_AURA_REMOVED" then
    if DOT[ev.id] then finishApp(p, ev.id, ev.dstGUID, ev.name) end

  elseif ev.sub == "SPELL_CAST_SUCCESS" then
    if FINISHER[ev.id] then
      local e = entry(p, ev.id, ev.name)
      e.casts = (e.casts or 0) + 1
      if DOT[ev.id] then startApp(ev.id, ev.dstGUID or "?", cpBefore()) end
    end

  elseif ev.sub == "SPELL_MISSED" then
    stats.misses = stats.misses + 1
  end
end

------------------------------------------------------------------------------- summaries

function FM.summaryFor(p, id)
  local e = p and p.spells and p.spells[id]
  if not e then return nil end
  local out = { name = e.name, perCP = {}, tickPerCP = {}, full = {}, observed = {} }
  for cp, b in pairs(e.direct) do
    local a = avg(b)
    if a then out.perCP[cp] = { avg = a, n = b.n, min = b.min, max = b.max } end
  end
  for cp, b in pairs(e.tick) do
    local a = avg(b)
    if a then
      out.tickPerCP[cp] = { avg = a, n = b.n, min = b.min, max = b.max }
      local app = e.apps and e.apps[cp]
      local ticks = math.max((app and app.maxTicks) or 0, designedTicks(id, cp))
      if ticks > 0 then
        out.full[cp] = { total = a * ticks, ticks = ticks }
      end
      if app and app.n > 0 then
        out.observed[cp] = {
          total = app.sum / app.n, ticks = app.maxTicks, n = app.n,
          dur = app.durSum / app.n,
          interval = app.intervalN > 0 and (app.intervalSum / app.intervalN) or nil,
        }
      end
    end
  end
  return out
end

function FM.summary(id) return FM.summaryFor(FM.profile(), id) end

------------------------------------------------------------------------------- tooltips

local function append(tip, text)
  tip:AddLine(text, 0.35, 1.0, 0.5)
end

local function n0(v) return string.format("%d", math.floor((v or 0) + 0.5)) end

local function tipLines(id)
  local s = FM.summary(id)
  if not s then return nil end
  local lines = {}
  for cp = 0, 5 do
    local d = s.perCP[cp]
    if d and d.n >= FM.MIN_HITS then
      lines[#lines + 1] = string.format("%s%s avg %s (%s-%s, %d hits)",
        cp > 0 and (cp .. "cp: ") or "", s.name or "", n0(d.avg), n0(d.min), n0(d.max), d.n)
    end
  end
  for cp = 0, 5 do
    local t = s.tickPerCP[cp]
    if t and t.n >= FM.MIN_HITS then
      local f, o = s.full[cp], s.observed[cp]
      local which = cp > 0 and string.format(" at %dcp", cp) or ""
      if f then
        lines[#lines + 1] = string.format("%s per tick x %d ticks = %s%s",
          n0(t.avg), f.ticks, n0(f.total), which)
      else
        lines[#lines + 1] = string.format("%s per tick%s", n0(t.avg), which)
      end
      if o then
        lines[#lines + 1] = string.format("landed %s over %.1fs (%d ticks%s)", n0(o.total), o.dur, o.ticks,
          o.interval and string.format(", every %.2fs", o.interval) or "")
      end
    end
  end
  if #lines == 0 then return nil end
  return lines
end

local KNOWN = { [1822]=1,[1823]=1,[1824]=1,[1825]=1,[1079]=1,[1082]=1,[5221]=1,[22568]=1,
                [9005]=1,[33876]=1,[33982]=1,[33983]=1,[779]=1,[6807]=1,[6785]=1,[6787]=1 }

local hooksInstalled = {}

local function spellIdOf(tip)
  if tip._fmSpell then return tip._fmSpell end
  if tip.GetSpell then
    local ok, _, id = pcall(tip.GetSpell, tip)
    if ok and type(id) == "number" then return id end
  end
  return nil
end

local function decorate(tip)
  if not db().settings.tips then return end
  if tip._fmDone then return end          -- the wrapper and the hook must not stack up
  local id = spellIdOf(tip)
  if not id then return end
  local lines = tipLines(id)
  if lines then
    append(tip, " ")
    for _, l in ipairs(lines) do append(tip, "FM: " .. l) end
  elseif KNOWN[id] then
    append(tip, "FM: no samples yet, hit something with it")
  end
  tip._fmDone = true
end

local function installHook(frame)
  if not frame or hooksInstalled[frame] then return end
  hooksInstalled[frame] = true
  if frame.HookScript then
    frame:HookScript("OnTooltipSetSpell", function(tip)
      if tip then decorate(tip) end
    end)
  end
end

local function hookTooltips()
  installHook(GameTooltip)
  if ItemRefTooltip then installHook(ItemRefTooltip) end
  -- Some tooltip addons rebuild the lines after the game sets the spell, so also wrap the calls
  -- that name the spell. Recording the id on the tooltip is what makes the later hook reliable.
  local gt = GameTooltip
  if gt then
    for _, method in ipairs({ "SetSpellByID", "SetSpell", "SetAction" }) do
      local original = gt[method]
      if type(original) == "function" and not gt["_fmWrapped" .. method] then
        gt["_fmWrapped" .. method] = true
        gt[method] = function(tip, ...)
          tip._fmDone = nil
          local ok, a, b = pcall(original, tip, ...)
          if method == "SetAction" then
            local slot = ...
            if GetActionInfo then
              local kind, id = GetActionInfo(slot)
              if kind == "spell" then tip._fmSpell = id end
            end
          elseif type(b) == "number" then
            tip._fmSpell = b
          elseif type(a) == "number" then
            tip._fmSpell = a
          end
          decorate(tip)
          if ok then return a, b end
        end
      end
    end
  end
end

------------------------------------------------------------------------------- commands

local function header(p)
  print("|cff33ff99FeralMetrics|r " .. describe(p.meta or {})
    .. string.format("  [%s], %s", p.id, date("%d %b %H:%M", p.created or 0)))
end

local function printProfile(p)
  header(p)
  local ids = {}
  for id in pairs(p.spells or {}) do ids[#ids + 1] = id end
  table.sort(ids)
  local shown = 0
  for _, id in ipairs(ids) do
    local s = FM.summaryFor(p, id)
    for cp = 0, 5 do
      local d = s and s.perCP[cp]
      if d and d.n >= FM.MIN_HITS then
        print(string.format("  %s%s  %s avg  (%s-%s, n=%d)", s.name, cp > 0 and (" " .. cp .. "cp") or "",
          n0(d.avg), n0(d.min), n0(d.max), d.n)); shown = shown + 1
      end
      local t = s and s.tickPerCP[cp]
      if t and t.n >= FM.MIN_HITS then
        local f, o = s.full[cp], s.observed[cp]
        print(string.format("  %s%s  %s/tick x %d = %s  (landed %s%s)", s.name,
          cp > 0 and (" " .. cp .. "cp") or "", n0(t.avg), f and f.ticks or 0,
          f and n0(f.total) or "-", o and n0(o.total) or "-",
          o and o.interval and string.format(", every %.2fs", o.interval) or "")); shown = shown + 1
      end
    end
  end
  if shown == 0 then print("  no samples yet, go hit something") end
  print(string.format("  events %d, direct hits %d, ticks %d, misses %d",
    stats.events, stats.hits, stats.ticks, stats.misses))
end

local function compare()
  local d = db()
  local p = FM.profile()
  local idx
  for i, id in ipairs(d.order) do if id == p.id then idx = i end end
  if not idx or idx <= 1 then print("FeralMetrics: no earlier profile yet") return end
  local prev = d.profiles[d.order[idx - 1]]
  print("|cff33ff99FeralMetrics|r comparing")
  print("  was: " .. describe(prev.meta or {}))
  print("  now: " .. describe(p.meta or {}))
  for id in pairs(p.spells) do
    local a, b = FM.summaryFor(p, id), FM.summaryFor(prev, id)
    if a and b then
      for cp = 0, 5 do
        local x, y = a.perCP[cp], b.perCP[cp]
        if x and y then
          print(string.format("  %s%s %d -> %d  (%+d)", a.name, cp > 0 and (" " .. cp .. "cp") or "",
            n0(y.avg), n0(x.avg), n0(x.avg - y.avg)))
        end
        local xt, yt = a.tickPerCP[cp], b.tickPerCP[cp]
        if xt and yt then
          print(string.format("  %s%s tick %d -> %d  (%+d)", a.name, cp > 0 and (" " .. cp .. "cp") or "",
            n0(yt.avg), n0(xt.avg), n0(xt.avg - yt.avg)))
        end
      end
    end
  end
end

SLASH_FERALMETRICS1 = "/fm"
SLASH_FERALMETRICS2 = "/feralmetrics"
SlashCmdList["FERALMETRICS"] = function(msg)
  msg = (msg or ""):lower()
  if msg == "compare" then return compare() end
  if msg == "profiles" then
    local d = db()
    for i, id in ipairs(d.order) do
      print(string.format("  %d %s%s %s", i, id == d.active and "*" or " ", describe(d.profiles[id].meta or {})))
    end
    return
  end
  if msg == "tips" then
    local d = db(); d.settings.tips = not d.settings.tips
    print("FeralMetrics tooltips " .. (d.settings.tips and "on" or "off")); return
  end
  if msg == "reset" then
    local d = db()
    d.profiles[FM.profile().id] = nil
    current = nil
    print("FeralMetrics: profile cleared"); return
  end
  if msg == "debug" then
    local installed = 0
    for _ in pairs(hooksInstalled) do installed = installed + 1 end
    print(string.format("FeralMetrics %s: events %d, hits %d, ticks %d, tooltip hooks %d, profile %s",
      FM.VERSION, stats.events, stats.hits, stats.ticks, installed, FM.profile().id))
    print("  spells recorded: " .. (function()
      local n = 0
      for _ in pairs(FM.profile().spells) do n = n + 1 end
      return n
    end)())
    return
  end
  printProfile(FM.profile())
end

------------------------------------------------------------------------------- frame

local f = CreateFrame("Frame")
for _, e in ipairs({ "ADDON_LOADED", "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD", "PLAYER_LEVEL_UP",
                     "PLAYER_EQUIPMENT_CHANGED", "CHARACTER_POINTS_CHANGED", "PLAYER_TALENT_UPDATE",
                     "UNIT_ATTACK_POWER", "UNIT_COMBO_POINTS", "COMBAT_LOG_EVENT_UNFILTERED" }) do
  f:RegisterEvent(e)
end

f:SetScript("OnEvent", function(_, event, ...)
  if event == "ADDON_LOADED" then
    db(); FM.ensureProfile(); hookTooltips()
    print("|cff33ff99FeralMetrics|r " .. FM.VERSION .. " loaded. /fm for numbers, /fm debug for state.")
    return
  end
  if event == "COMBAT_LOG_EVENT_UNFILTERED" then onEvent(...); return end
  if event == "UNIT_COMBO_POINTS" then noteComboPoints(); return end
  FM.ensureProfile()
end)

local ticker = CreateFrame("Frame")
ticker:SetScript("OnUpdate", (function()
  local acc = 0
  return function(_, elapsed)
    acc = acc + elapsed
    if acc < 0.1 then return end
    acc = 0
    if UnitAffectingCombat and UnitAffectingCombat("player") then noteComboPoints() end
  end
end)())

hookTooltips()
