-- Smoke test: feed the addon a fake fight and check the numbers it reports.
local stub = dofile("tests/stub.lua")

local FM = {}
local chunk = assert(loadfile("FeralMetrics.lua"))
chunk("FeralMetrics", FM)

local checks, fails = 0, 0
local function ok(cond, msg)
  checks = checks + 1
  if not cond then fails = fails + 1; io.write("FAIL " .. msg .. "\n") end
end
local function near(a, b, tol, msg)
  ok(a and math.abs(a - b) <= (tol or 0.01), msg .. string.format(" (got %s, want %s)", tostring(a), tostring(b)))
end

-- boot
stub.fire("ADDON_LOADED", "FeralMetrics")
stub.fire("PLAYER_ENTERING_WORLD")
ok(FM.profile().id ~= nil, "a profile exists after login")
local firstProfile = FM.profile().id

-- Rake: three ticks of 40, 41, 39 over 9 seconds
stub.cp = 0
stub.log("SPELL_AURA_APPLIED", "Creature-1", 1822, "Rake", 0)
stub.time = stub.time + 2; stub.log("SPELL_PERIODIC_DAMAGE", "Creature-1", 1822, "Rake", 40)
stub.time = stub.time + 2; stub.log("SPELL_PERIODIC_DAMAGE", "Creature-1", 1822, "Rake", 41)
stub.time = stub.time + 2; stub.log("SPELL_PERIODIC_DAMAGE", "Creature-1", 1822, "Rake", 39)
stub.log("SPELL_AURA_REMOVED", "Creature-1", 1822, "Rake", 0)

local rake = FM.summary("Rake")
ok(rake ~= nil, "rake has samples")
near(rake.tickPerCP[0].avg, 40, 0.01, "rake tick average")
ok(rake.tickPerCP[0].n == 3, "rake counted three ticks")
ok(rake.full[0].ticks == 3, "rake full ticks are its designed three")
near(rake.full[0].total, 120, 0.01, "rake full total = tick x ticks")
near(rake.observed[0].interval, 2, 0.3, "rake tick interval measured at 2s")

-- Rip at five combo points, clipped to four ticks
stub.cp = 5
stub.fire("UNIT_COMBO_POINTS")
stub.log("SPELL_CAST_SUCCESS", "Creature-1", 1079, "Rip", 0)
stub.log("SPELL_AURA_APPLIED", "Creature-1", 1079, "Rip", 0)
for _, dmg in ipairs({ 30, 31, 29, 30 }) do
  stub.time = stub.time + 2; stub.log("SPELL_PERIODIC_DAMAGE", "Creature-1", 1079, "Rip", dmg)
end
stub.log("SPELL_AURA_REMOVED", "Creature-1", 1079, "Rip", 0)

local rip = FM.summary("Rip")
ok(rip ~= nil, "rip has samples")
ok(rip.tickPerCP[5] ~= nil, "rip recorded against five combo points")
near(rip.tickPerCP[5].avg, 30, 0.01, "rip tick average")
ok(rip.full[5].ticks == 8, "rip full ticks use the designed count, not the clipped one")
near(rip.full[5].total, 240, 0.01, "rip full total = per tick x designed ticks")
near(rip.observed[5].total, 120, 0.01, "rip observed total")

-- Ferocious Bite as a five point direct hit
stub.cp = 5
stub.fire("UNIT_COMBO_POINTS")
stub.log("SPELL_DAMAGE", "Creature-1", 22568, "Ferocious Bite", 300)
stub.log("SPELL_DAMAGE", "Creature-1", 22568, "Ferocious Bite", 320, true)
local bite = FM.summary("Ferocious Bite")
ok(bite.perCP[5] ~= nil, "bite recorded per combo point")
near(bite.perCP[5].avg, 310, 0.01, "bite average of the two hits")
ok(bite.perCP[5].max == 320, "bite max tracked")
ok(bite.perCP[5].n == 2, "bite hit count")

-- tooltip shows the numbers, and shows nothing for a spell with no samples
local lines = stub.showTooltip(1822, "Rake")
local joined = table.concat(lines, " | ")
ok(joined:find("per tick") ~= nil, "tooltip has a tick line")
ok(joined:find("FM:") ~= nil, "tooltip lines are tagged")
ok(#stub.showTooltip(999999, "Not A Spell") == 0, "unknown spell adds nothing")

-- changing a stat starts a new profile and keeps the old numbers apart
stub.ap = 400
stub.fire("UNIT_ATTACK_POWER")
local second = FM.profile().id
ok(second ~= firstProfile, "a new profile starts when attack power changes")
ok(FM.summary("Rake") == nil, "the new profile starts empty")
ok(FM.summaryFor(FeralMetricsDB.profiles[firstProfile], "Rake") ~= nil, "the old profile kept its numbers")

-- and the old ones survive a reload of the saved variables
local saved = FeralMetricsDB
FeralMetricsDB = saved
FM.ensureProfile()
ok(FeralMetricsDB.profiles[firstProfile] ~= nil, "saved variables hold both profiles")

io.write(string.format("%d checks, %d failed\n", checks, fails))
if fails > 0 then os.exit(1) end
