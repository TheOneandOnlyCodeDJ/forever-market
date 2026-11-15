-- FeralMetrics: measured damage for a feral druid on WoW Forever.
--
-- Real numbers only: every figure is the mean of damage events the client actually fired.
--
-- Two rules learned on this client:
--   1. Nothing is keyed on a hardcoded spell id. Forever has its own ids and extra ranks, so
--      samples are stored by spell NAME and every player damage event is captured, not only the
--      ones on a list.
--   2. Nothing may throw. Client APIs go through a wrapper, and the first error is said out loud
--      in chat instead of disappearing inside an event handler.

local ADDON, FM = ...

FM.VERSION = "0.2.0"
FM.MIN_HITS = 1
FM.CP_WINDOW = 2.0

local FINISHER_NAMES = { ["Rip"] = true, ["Ferocious Bite"] = true, ["Maim"] = true }
local DOT_NAMES = { ["Rip"] = true, ["Rake"] = true, ["Pounce"] = true, ["Lacerate"] = true }
-- ticks the spell is meant to deliver; a clipped bleed only ever shows fewer
local DESIGNED_TICKS = {
  ["Rip"] = { [1] = 4, [2] = 5, [3] = 6, [4] = 7, [5] = 8 },
  ["Rake"] = { [0] = 3 }, ["Pounce"] = { [0] = 3 }, ["Lacerate"] = { [0] = 5 },
}
local KNOWN_NAMES = { ["Rake"] = true, ["Rip"] = true, ["Ferocious Bite"] = true, ["Shred"] = true,
                      ["Claw"] = true, ["Mangle"] = true, ["Swipe"] = true, ["Maul"] = true,
                      ["Ravage"] = true, ["Pounce"] = true }

local function now() return (GetTime and GetTime()) or time() end

local reported = false
local function report(where, err)
  if reported or not print then return end
  reported = true
  print("|cffff5555FeralMetrics|r error in " .. tostring(where) .. ": " .. tostring(err))
end

local function safe(f, ...)
  if type(f) ~= "function" then return nil end
  local ok, a, b, c, d = pcall(f, ...)
  if not ok then return nil end
  return a, b, c, d
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

------------------------------------------------------------------------------- fingerprint

local function talentPoints()
  local parts = {}
  for tab = 1, (safe(GetNumTalentTabs) or 0) do
    local name, _, points = safe(GetTalentTabInfo, tab)
    if name or points then
      parts[#parts + 1] = string.format("%s=%d", tostring(name or tab), points or 0)
    end
  end
  return table.concat(parts, ",")
end

local function snapshot()
  local _, str = safe(UnitStat, "player", 1)
  local _, agi = safe(UnitStat, "player", 2)
  local _, sta = safe(UnitStat, "player", 3)
  local base, pos, neg = safe(UnitAttackPower, "player")
  local mh = safe(GetInventoryItemID, "player", 16) or 0
  local wname, _, _, _, _, _, wspeed = safe(GetItemInfo, mh)
  return {
    level = safe(UnitLevel, "player") or 0,
    str = str or 0, agi = agi or 0, sta = sta or 0,
    ap = (base or 0) + (pos or 0) + (neg or 0),
    crit = safe(GetCritChance) or 0,
    weapon = mh, wname = wname, wspeed = wspeed or 0,
    talents = talentPoints(),
  }
end

local function fingerprint(s)
  return string.format("L%d|AP%d|S%d|A%d|C%.2f|W%d|T%s",
    s.level, s.ap, s.str, s.agi, s.crit, s.weapon, s.talents)
end

local function hash(s)
  local h = 2166136261
  for i = 1, #s do
    local b = s:byte(i)
    if bit and bit.bxor then
      h = bit.band(bit.bxor(h, b) * 16777619, 0xFFFFFFFF)
    else
      h = (h * 16777619 + b) % 4294967296
    end
  end
  return string.format("%08x", h)
end

local function describe(s)
  return string.format("level %d, %d AP, %d Str, %d Agi, %.2f%% crit, %s",
    s.level or 0, s.ap or 0, s.str or 0, s.agi or 0, s.crit or 0, s.wname or "no weapon")
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

function FM.profile()
  if current then return current end
  local ok, p = pcall(FM.ensureProfile)
  if ok and p then return p end
  report("profile", p)
  return { id = "fallback", created = time(), meta = {}, spells = {} }
end

------------------------------------------------------------------------------- aggregation

local function entry(p, name)
  local e = p.spells[name]
  if not e then
    e = { name = name, direct = {}, tick = {}, apps = {} }
    p.spells[name] = e
  end
  return e
end

local function addHit(t, cp, amount, isCrit)
  local b = t[cp]
  if not b then b = { n = 0, sum = 0, crits = 0 }; t[cp] = b end
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
  local v = safe(GetComboPoints, "player", "target")
  if type(v) == "number" then cp = v end
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
local function akey(id, dest) return tostring(id) .. "|" .. tostring(dest) end

local function startApp(id, dest, cp, name)
  apps[akey(id, dest)] = { start = now(), cp = cp or 0, ticks = 0, amount = 0,
                           lastTick = nil, intervalSum = 0, intervalN = 0, name = name }
end

local function onTick(id, dest, amount)
  local a = apps[akey(id, dest)]
  if not a then return nil end
  if a.lastTick then
    a.intervalSum = a.intervalSum + (now() - a.lastTick)
    a.intervalN = a.intervalN + 1
  end
  a.lastTick = now()
  a.ticks = a.ticks + 1
  a.amount = a.amount + amount
  return a.cp, a.name
end

local function finishApp(p, id, dest)
  local k = akey(id, dest)
  local a = apps[k]
  if not a then return end
  apps[k] = nil
  if a.ticks == 0 then return end
  local e = entry(p, a.name or ("spell " .. tostring(id)))
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

local stats = { events = 0, hits = 0, ticks = 0, misses = 0, foreign = 0 }

local function parse(...)
  local info
  if CombatLogGetCurrentEventInfo then
    info = { CombatLogGetCurrentEventInfo() }   -- no extra parens: they would truncate to one value
  else
    info = { ... }
  end
  return {
    sub = info[2], srcGUID = info[4], dstGUID = info[7],
    id = info[10], name = info[11], amount = tonumber(info[13]) or 0,
    crit = info[19] and true or false,
  }
end

local function cleanName(n)
  if not n then return nil end
  return (tostring(n):gsub("%s*%(Rank %d+%)$", ""))
end

local function combatEvent(...)
  local ev = parse(...)
  stats.events = stats.events + 1
  noteComboPoints()
  if not ev.sub then return end
  if ev.srcGUID ~= safe(UnitGUID, "player") then stats.foreign = stats.foreign + 1; return end
  local p = FM.profile()
  local name = cleanName(ev.name)

  if ev.sub == "SPELL_DAMAGE" then
    if not name or ev.amount <= 0 then return end
    local cp = FINISHER_NAMES[name] and cpBefore() or 0
    addHit(entry(p, name).direct, cp, ev.amount, ev.crit)
    stats.hits = stats.hits + 1

  elseif ev.sub == "SPELL_PERIODIC_DAMAGE" then
    if not name or ev.amount <= 0 then return end
    local cp = onTick(ev.id, ev.dstGUID, ev.amount)
    addHit(entry(p, name).tick, cp or 0, ev.amount, ev.crit)
    stats.ticks = stats.ticks + 1

  elseif ev.sub == "SPELL_AURA_APPLIED" or ev.sub == "SPELL_AURA_REFRESH" then
    if name and (DOT_NAMES[name] or apps[akey(ev.id, ev.dstGUID)]) then
      finishApp(p, ev.id, ev.dstGUID)
      startApp(ev.id, ev.dstGUID, FINISHER_NAMES[name] and cpBefore() or 0, name)
    end

  elseif ev.sub == "SPELL_AURA_REMOVED" then
    finishApp(p, ev.id, ev.dstGUID)

  elseif ev.sub == "SPELL_CAST_SUCCESS" then
    if name and DOT_NAMES[name] and not apps[akey(ev.id, ev.dstGUID)] then
      startApp(ev.id, ev.dstGUID, FINISHER_NAMES[name] and cpBefore() or 0, name)
    end

  elseif ev.sub == "SPELL_MISSED" then
    stats.misses = stats.misses + 1
  end
end

local function onEvent(...)
  local ok, err = pcall(combatEvent, ...)
  if not ok then report("combat log", err) end
end
------------------------------------------------------------------------------- summaries

local function designedTicks(name, cp)
  local t = DESIGNED_TICKS[name]
  if type(t) ~= "table" then return 0 end
  return t[cp] or t[0] or 0
end

function FM.summaryFor(p, name)
  local e = p and p.spells and p.spells[name]
  if not e then return nil end
  local out = { name = name, perCP = {}, tickPerCP = {}, full = {}, observed = {} }
  for cp, b in pairs(e.direct) do
    local a = avg(b)
    if a then out.perCP[cp] = { avg = a, n = b.n, min = b.min, max = b.max } end
  end
  for cp, b in pairs(e.tick) do
    local a = avg(b)
    if a then
      out.tickPerCP[cp] = { avg = a, n = b.n, min = b.min, max = b.max }
      local app = e.apps and e.apps[cp]
      local ticks = math.max((app and app.maxTicks) or 0, designedTicks(name, cp))
      if ticks > 0 then out.full[cp] = { total = a * ticks, ticks = ticks } end
      if app and app.n > 0 then
        out.observed[cp] = { total = app.sum / app.n, ticks = app.maxTicks, n = app.n,
                             dur = app.durSum / app.n,
                             interval = app.intervalN > 0 and (app.intervalSum / app.intervalN) or nil }
      end
    end
  end
  return out
end

function FM.summary(name) return FM.summaryFor(FM.profile(), name) end

------------------------------------------------------------------------------- tooltips

local function append(tip, text) tip:AddLine(text, 0.35, 1.0, 0.5) end
local function n0(v) return string.format("%d", math.floor((v or 0) + 0.5)) end

local function linesFor(name)
  local s = FM.summary(name)
  if not s then return nil end
  local out = {}
  for cp = 0, 5 do
    local d = s.perCP[cp]
    if d and d.n >= FM.MIN_HITS then
      out[#out + 1] = string.format("%s%s avg %s (%s-%s, %d hits)",
        cp > 0 and (cp .. "cp ") or "", name, n0(d.avg), n0(d.min), n0(d.max), d.n)
    end
  end
  for cp = 0, 5 do
    local t = s.tickPerCP[cp]
    if t and t.n >= FM.MIN_HITS then
      local f, o = s.full[cp], s.observed[cp]
      local which = cp > 0 and string.format(" at %dcp", cp) or ""
      if f then
        out[#out + 1] = string.format("%s %s per tick x %d = %s%s", name, n0(t.avg), f.ticks, n0(f.total), which)
      else
        out[#out + 1] = string.format("%s %s per tick%s", name, n0(t.avg), which)
      end
      if o then
        out[#out + 1] = string.format("   landed %s over %.1fs (%d ticks%s)", n0(o.total), o.dur, o.ticks,
          o.interval and string.format(", every %.2fs", o.interval) or "")
      end
    end
  end
  if #out == 0 then return nil end
  return out
end

local function resolveName(tip)
  if tip._fmName then return tip._fmName end
  if tip.GetSpell then
    local ok, name, id = pcall(tip.GetSpell, tip)
    if ok and name then return cleanName(name) end
    if ok and id then
      local n = safe(GetSpellInfo, id)
      if n then return cleanName(n) end
    end
  end
  return nil
end

local function decorate(tip)
  if not db().settings.tips or tip._fmDone then return end
  local name = resolveName(tip)
  if not name then return end
  local lines = linesFor(name)
  if lines then
    tip._fmDone = true
    append(tip, " ")
    for _, l in ipairs(lines) do append(tip, "FM: " .. l) end
  elseif KNOWN_NAMES[name] then
    tip._fmDone = true
    append(tip, "FM: no samples yet")
  end
end

local hooked = {}

local function installHook(frame)
  if not frame or hooked[frame] then return end
  hooked[frame] = true
  if frame.HookScript then
    frame:HookScript("OnTooltipSetSpell", function(tip) decorate(tip) end)
  end
  for _, method in ipairs({ "SetSpellByID", "SetSpell", "SetAction" }) do
    local original = frame[method]
    if type(original) == "function" and not frame["_fmw" .. method] then
      frame["_fmw" .. method] = true
      frame[method] = function(self, ...)
        self._fmDone = nil
        self._fmName = nil
        if method == "SetAction" then
          local kind, id = safe(GetActionInfo, ...)
          if kind == "spell" and id then
            self._fmName = cleanName(safe(GetSpellInfo, id))
          end
        end
        local a, b = pcall(original, self, ...)
        if method == "SetSpellByID" then
          self._fmName = cleanName(safe(GetSpellInfo, ...))
        elseif method == "SetSpell" then
          self._fmName = cleanName(...)
        end
        decorate(self)
        return a, b
      end
    end
  end
end

local function hookTooltips()
  installHook(GameTooltip)
  installHook(ItemRefTooltip)
end

------------------------------------------------------------------------------- commands

local function printProfile(p)
  print("|cff33ff99FeralMetrics|r " .. describe(p.meta or {}) ..
    string.format("   [%s] %s", p.id, date("%d %b %H:%M", p.created or 0)))
  local names = {}
  for n in pairs(p.spells or {}) do names[#names + 1] = n end
  table.sort(names)
  local shown = 0
  for _, n in ipairs(names) do
    local s = FM.summaryFor(p, n)
    for cp = 0, 5 do
      local d = s and s.perCP[cp]
      if d and d.n >= FM.MIN_HITS then
        print(string.format("  %s%s %s avg (%s-%s, n=%d)", n, cp > 0 and (" " .. cp .. "cp") or "",
          n0(d.avg), n0(d.min), n0(d.max), d.n)); shown = shown + 1
      end
      local t = s and s.tickPerCP[cp]
      if t and t.n >= FM.MIN_HITS then
        local f, o = s.full[cp], s.observed[cp]
        print(string.format("  %s%s %s/tick x %d = %s (landed %s%s)", n, cp > 0 and (" " .. cp .. "cp") or "",
          n0(t.avg), f and f.ticks or 0, f and n0(f.total) or "-", o and n0(o.total) or "-",
          o and o.interval and string.format(", every %.2fs", o.interval) or "")); shown = shown + 1
      end
    end
  end
  if shown == 0 then print("  no samples yet, hit something") end
  print(string.format("  events %d, own hits %d, ticks %d, misses %d, other sources %d",
    stats.events, stats.hits, stats.ticks, stats.misses, stats.foreign))
end

local function compare()
  local d = db()
  local p = FM.profile()
  local idx
  for i, id in ipairs(d.order) do if id == p.id then idx = i end end
  if not idx or idx <= 1 then print("FeralMetrics: no earlier profile yet") return end
  local prev = d.profiles[d.order[idx - 1]]
  print("  was: " .. describe(prev.meta or {}))
  print("  now: " .. describe(p.meta or {}))
  for name in pairs(p.spells) do
    local a, b = FM.summaryFor(p, name), FM.summaryFor(prev, name)
    if a and b then
      for cp = 0, 5 do
        local x, y = a.perCP[cp], b.perCP[cp]
        if x and y then
          print(string.format("  %s%s %s -> %s (%+d)", name, cp > 0 and (" " .. cp .. "cp") or "",
            n0(y.avg), n0(x.avg), n0(x.avg - y.avg)))
        end
        local xt, yt = a.tickPerCP[cp], b.tickPerCP[cp]
        if xt and yt then
          print(string.format("  %s%s tick %s -> %s (%+d)", name, cp > 0 and (" " .. cp .. "cp") or "",
            n0(yt.avg), n0(xt.avg), n0(xt.avg - yt.avg)))
        end
      end
    end
  end
end

SLASH_FERALMETRICS1 = "/feral"
SLASH_FERALMETRICS2 = "/fmetrics"
SLASH_FERALMETRICS3 = "/feralm"
SlashCmdList["FERALMETRICS"] = function(msg)
  msg = (msg or ""):lower()
  if msg == "compare" then return compare() end
  if msg == "profiles" then
    local d = db()
    for i, id in ipairs(d.order) do
      print(string.format("  %d %s %s", i, id == d.active and "*" or " ", describe(d.profiles[id].meta or {})))
    end
    return
  end
  if msg == "tips" then
    local d = db(); d.settings.tips = not d.settings.tips
    print("FeralMetrics tooltips " .. (d.settings.tips and "on" or "off")); return
  end
  if msg == "reset" then
    local d = db(); d.profiles[FM.profile().id] = nil; current = nil
    print("FeralMetrics: profile cleared"); return
  end
  if msg == "debug" then
    local n = 0
    for _ in pairs(hooked) do n = n + 1 end
    print(string.format("FeralMetrics %s: events %d, own %d, ticks %d, foreign %d, tooltip frames %d",
      FM.VERSION, stats.events, stats.hits, stats.ticks, stats.foreign, n))
    local names = {}
    for name in pairs(FM.profile().spells) do names[#names + 1] = name end
    table.sort(names)
    print("  recorded: " .. (#names > 0 and table.concat(names, ", ") or "nothing"))
    return
  end
  printProfile(FM.profile())
end

------------------------------------------------------------------------------- frame

local f = CreateFrame("Frame")
for _, e in ipairs({ "ADDON_LOADED", "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD", "PLAYER_LEVEL_UP",
                     "PLAYER_EQUIPMENT_CHANGED", "CHARACTER_POINTS_CHANGED", "PLAYER_TALENT_UPDATE",
                     "UNIT_ATTACK_POWER", "UNIT_COMBO_POINTS", "COMBAT_LOG_EVENT_UNFILTERED" }) do
  pcall(f.RegisterEvent, f, e)
end

local function dispatch(event, ...)
  if event == "ADDON_LOADED" then
    db()
    FM.ensureProfile()
    hookTooltips()
    print("|cff33ff99FeralMetrics|r " .. FM.VERSION .. " loaded. /feral for numbers.")
    return
  end
  if event == "COMBAT_LOG_EVENT_UNFILTERED" then onEvent(...) return end
  if event == "UNIT_COMBO_POINTS" then noteComboPoints() return end
  FM.ensureProfile()
end

f:SetScript("OnEvent", function(_, event, ...)
  local ok, err = pcall(dispatch, event, ...)
  if not ok then report(event, err) end
end)

local ticker = CreateFrame("Frame")
ticker:SetScript("OnUpdate", (function()
  local acc = 0
  return function(_, elapsed)
    acc = acc + elapsed
    if acc < 0.1 then return end
    acc = 0
    if safe(UnitAffectingCombat, "player") then noteComboPoints() end
  end
end)())
