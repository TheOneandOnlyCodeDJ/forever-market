import csv
import io

from fm import http
from fm.db import log_sync
from fm.sync_items import FOREVER, WAGO, _int

TABLES = ["SpellName", "SpellEffect", "SpellReagents", "SkillLineAbility"]
PROFESSIONS = {171: "Alchemy", 164: "Blacksmithing", 333: "Enchanting", 202: "Engineering",
               185: "Cooking", 129: "First Aid", 165: "Leatherworking", 197: "Tailoring",
               186: "Mining", 356: "Fishing"}


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def abilities(sla):
    """spell id -> (profession, min_skill, category_id); a repeated spell keeps its lowest rank."""
    out = {}
    for r in sla:
        prof = PROFESSIONS.get(int(r["SkillLine"]))
        if prof is None:
            continue
        spell, rank = int(r["Spell"]), int(r["MinSkillLineRank"])
        if spell not in out or rank < out[spell][1]:
            out[spell] = (prof, rank, _int(r["TradeSkillCategoryID"]))
    return out


def reagents(sr):
    return [(int(r["SpellID"]), int(r[f"Reagent_{i}"]), int(r[f"ReagentCount_{i}"]))
            for r in sr for i in range(8)
            if int(r[f"Reagent_{i}"]) and int(r[f"ReagentCount_{i}"])]


def outputs(se):
    return [(int(r["SpellID"]), int(r["EffectItemType"]),
             min(max(int(float(r["EffectBasePointsF"] or 1)), 1), 200))
            for r in se if r["Effect"] == "24" and int(r["EffectItemType"]) > 0]


def build(names, se, sr, sla):
    """Profession spells that have reagents -> (spell, spell_reagent, craft_output) rows."""
    abil = abilities(sla)
    reag = [r for r in reagents(sr) if r[0] in abil]
    keep = {r[0] for r in reag}
    name = {int(r["ID"]): r["Name_lang"] for r in names}
    spells = [(s, name.get(s), *abil[s]) for s in sorted(keep)]
    return spells, reag, [o for o in outputs(se) if o[0] in keep]


def run(conn):
    data = {}
    for table in TABLES:
        source = f"wago_{table.lower()}"
        try:
            data[table] = rows(http.get(WAGO.format(table=table, build=FOREVER), ttl=7 * 86400).decode("utf-8"))
            log_sync(conn, source, len(data[table]), f"{table} build {FOREVER}")
        except Exception as e:
            log_sync(conn, source, None, f"FAILED: {e}")
            print(f"{source}: FAILED: {e}; recipes not updated")
            return [source]
    spells, reag, outs = build(*(data[t] for t in TABLES))
    conn.execute("DELETE FROM spell")
    conn.execute("DELETE FROM spell_reagent")
    conn.execute("DELETE FROM craft_output")
    conn.executemany("INSERT INTO spell VALUES (?,?,?,?,?)", spells)
    conn.executemany("INSERT INTO spell_reagent VALUES (?,?,?)", reag)
    conn.executemany("INSERT INTO craft_output VALUES (?,?,?)", outs)
    log_sync(conn, "recipes", len(spells), f"reagents={len(reag)} outputs={len(outs)}")
    print(f"recipes: {len(spells)} spells, {len(reag)} reagent rows, {len(outs)} output rows")
    return []
