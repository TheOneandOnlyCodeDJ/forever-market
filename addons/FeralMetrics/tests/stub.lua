-- Minimal Widget/Frame stand-in so the addon can run under plain Lua outside the game.
local stub = { time = 0, cp = 0, ap = 250, events = {}, scripts = {}, tooltips = {} }

local Widget = {}
Widget.__index = Widget
function Widget:RegisterEvent(e) self.registered[e] = true end
function Widget:SetScript(n, f) self.scripts[n] = f end
function Widget:HookScript(n, f) self.scripts[n] = f end
function Widget:GetName() return self.name end

function CreateFrame(kind, name)
  local f = setmetatable({ kind = kind, name = name, registered = {}, scripts = {} }, Widget)
  stub.events[#stub.events + 1] = f
  return f
end

function stub.fire(event, ...)
  for _, f in ipairs(stub.events) do
    if f.registered[event] and f.scripts.OnEvent then f.scripts.OnEvent(f, event, ...) end
  end
end

-- game api
function GetTime() return stub.time end
function time() return 1700000000 end
function date(fmt, t) return os.date(fmt, t) end
function UnitGUID(u) return "Player-1" end
function UnitLevel(u) return stub.level or 33 end
function UnitClass(u) return "Druid", "DRUID" end
function UnitStat(u, i)
  if i == 1 then return 0, stub.str or 68 end
  if i == 2 then return 0, stub.agi or 91 end
  if i == 3 then return 0, stub.sta or 120 end
  return 0, 40
end
function UnitAttackPower(u) return stub.ap, 0, 0 end
function GetCritChance() return stub.crit or 5.12 end
function GetInventoryItemID(u, slot) return 279844 end
function GetItemInfo(id) return "Striking Staff", "item:279844", 3, 36, 36, "Weapon", 3.10 end
function GetNumTalentTabs() return 3 end
function GetTalentTabInfo(tab)
  local names = { "Balance", "Feral Combat", "Restoration" }
  local pts = stub.talents or { 0, 21, 0 }
  return names[tab], "", pts[tab]
end
function GetComboPoints(a, b) return stub.cp end
function UnitAffectingCombat(u) return stub.inCombat ~= false end
local SPELL_NAMES = { [1822]="Rake",[1823]="Rake",[1824]="Rake",[1825]="Rake",[1079]="Rip",
                      [22568]="Ferocious Bite",[5221]="Shred",[1082]="Claw" }
function GetSpellInfo(id) return SPELL_NAMES[id] or ("Spell" .. tostring(id)) end

bit = bit or {}
function bit.bxor(a, b)
  local r, p = 0, 1
  for _ = 1, 32 do
    if (a % 2) ~= (b % 2) then r = r + p end
    a, b, p = math.floor(a / 2), math.floor(b / 2), p * 2
  end
  return r
end
function bit.band(a) return a % 4294967296 end

SlashCmdList = {}
function stub.slash(msg) SlashCmdList["FERALMETRICS"](msg) end

-- combat log
stub.cleu = nil
function CombatLogGetCurrentEventInfo() return unpack(stub.cleu) end

-- Forever payload: an extra flag field per unit, so spellID lands at 12 and amount at 15
function stub.log(sub, dstGUID, spellID, spellName, amount, crit)
  stub.time = stub.time + 0.2
  local info = { stub.time, sub, false,
                 "Player-1", "Lain", 0x511, 0,
                 dstGUID or "Creature-1", "Mob", 0, 0,
                 spellID, spellName, 1, amount or 0, 0, 1, 0, 0, 0 }
  if crit then info[21] = true end
  stub.cleu = info
  stub.fire("COMBAT_LOG_EVENT_UNFILTERED")
end
-- and the older layout, to prove the parser handles both
function stub.logClassic(sub, dstGUID, spellID, spellName, amount, crit)
  stub.time = stub.time + 0.2
  local info = { stub.time, sub, false, "Player-1", "Lain", 0x511, dstGUID or "Creature-1", "Mob", 0,
                 spellID, spellName, 1, amount or 0 }
  if crit then info[19] = true end
  stub.cleu = info
  stub.fire("COMBAT_LOG_EVENT_UNFILTERED")
end

-- tooltip
local Tooltip = {}
Tooltip.__index = Tooltip
function Tooltip:GetSpell() return self.spellName, self.spellID end
function Tooltip:SetSpellByID(id)
  self.spellID = id
  self.spellName = GetSpellInfo(id)
  self.lines = {}
end
function Tooltip:AddLine(text) self.lines[#self.lines + 1] = text end
function Tooltip:numLines() return #self.lines end
GameTooltip = setmetatable({ spellID = nil, lines = {}, scripts = {} }, Tooltip)
function GameTooltip:HookScript(n, f) self.scripts[n] = f end
function stub.showTooltip(id, name)
  GameTooltip._fmDone = nil
  GameTooltip._fmName = nil
  GameTooltip:SetSpellByID(id)
  if name then GameTooltip.spellName = name end
  if GameTooltip.scripts.OnTooltipSetSpell then
    GameTooltip.scripts.OnTooltipSetSpell(GameTooltip)
  end
  return GameTooltip.lines
end

stub.printed = {}
function print(...)
  local parts = {}
  for i = 1, select("#", ...) do parts[#parts + 1] = tostring((select(i, ...))) end
  stub.printed[#stub.printed + 1] = table.concat(parts, " ")
end

return stub
