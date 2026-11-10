"""Audit and fill the TradeSkillMaster item groups against the local item table.

The groups are stored in SavedVariables as flat path strings, so this edits the file's text
directly: one entry per item, one entry per new group path. Assignment is mechanical
(class, subclass, quality, bonding) so the result is explainable and repeatable.
"""
from __future__ import annotations

import datetime
import shutil
import sqlite3
from pathlib import Path

from fm import lua_table, paths

SV = Path(paths.CLIENT_DIR) / "WTF/Account/250808230#1/SavedVariables/TradeSkillMaster.lua"
ITEMS_MARK = '["p@Default@userData@items"] = {'
GROUPS_MARK = '["p@Default@userData@groups"] = {'

TRADE_GOODS = {0: "Trade Goods`Other Trade Goods", 1: "Trade Goods`Cloth", 2: "Trade Goods`Leather & Hides",
               3: "Trade Goods`Leather & Hides", 4: "Trade Goods`Ore, Bars & Stone",
               5: "Trade Goods`Ore, Bars & Stone", 6: "Trade Goods`Engineering Parts",
               7: "Trade Goods`Engineering Parts", 8: "Trade Goods`Herbs", 9: "Trade Goods`Herbs",
               10: "Trade Goods`Elemental", 11: "Trade Goods`Gems & Pearls",
               12: "Trade Goods`Enchanting Materials", 15: "Trade Goods`Other Trade Goods"}
CONSUMABLES = {0: "Consumables`Food & Drink", 1: "Consumables`Potions", 2: "Consumables`Elixirs",
               3: "Consumables`Elixirs", 4: "Consumables`Item Enhancements", 5: "Consumables`Food & Drink",
               6: "Consumables`Bandages", 7: "Consumables`Food & Drink", 8: "Consumables`Item Enhancements",
               14: "Consumables`Devices", 15: "Consumables`Bombs & Explosives"}
WEAPONS = {0: "Gear`One-Hand Weapons", 1: "Gear`One-Hand Weapons", 2: "Gear`Ranged & Wands",
           3: "Gear`Ranged & Wands", 4: "Gear`One-Hand Weapons", 5: "Gear`One-Hand Weapons",
           6: "Gear`One-Hand Weapons", 7: "Gear`Two-Hand Weapons", 8: "Gear`Two-Hand Weapons",
           10: "Gear`Two-Hand Weapons", 13: "Gear`Ranged & Wands", 15: "Gear`One-Hand Weapons",
           16: "Gear`Ranged & Wands", 18: "Gear`Ranged & Wands", 19: "Gear`One-Hand Weapons"}
ARMOUR = {0: "Gear`Cloth Armour", 1: "Gear`Cloth Armour", 2: "Gear`Leather Armour", 3: "Gear`Mail Armour",
          4: "Gear`Plate Armour", 5: "Gear`Shirts & Tabards", 6: "Gear`Shields",
          7: "Gear`Relics", 8: "Gear`Relics", 9: "Gear`Relics"}
RECIPES = {1: "Recipes`Tailoring", 2: "Recipes`Leatherworking", 3: "Recipes`Engineering",
           4: "Recipes`Blacksmithing", 5: "Recipes`Cooking", 6: "Recipes`Alchemy",
           7: "Recipes`First Aid", 8: "Recipes`Enchanting", 9: "Recipes`Fishing",
           0: "Recipes`Books"}


def target(cls, sub, quality, bonding):
    """Group path for one item, or None when it should stay out (soulbound, no class)."""
    if bonding == 1:
        return None
    if cls == 0:
        return CONSUMABLES.get(sub, "Consumables`Other")
    if cls == 1:
        return "Bags`Bags & Containers"
    if cls == 2:
        if (quality or 0) >= 3:
            return "Gear`Rare Weapons"
        if sub in (9, 11, 17, 20):  # thrown, unarmed, fishing pole, crossbow oddities
            return "Gear`Ranged & Wands"
        return WEAPONS.get(sub, "Gear`One-Hand Weapons")
    if cls == 4:
        if sub in (5, 7, 8, 9):
            return ARMOUR[sub]
        if (quality or 0) >= 3:
            return "Gear`Rare Armour"
        return ARMOUR.get(sub, "Gear`Cloth Armour")
    if cls == 5:
        return "Trade Goods`Other Trade Goods"
    if cls == 6:
        return "Ammo`Arrows & Bullets"
    if cls == 7:
        return TRADE_GOODS.get(sub, "Trade Goods`Other Trade Goods")
    if cls == 9:
        return RECIPES.get(sub, "Recipes`Books")
    if cls in (12, 13):
        return "Misc`Cards & Quest Items"
    if cls == 15:
        if sub == 2:
            return "Mounts & Pets`Pets"
        if sub == 5:
            return "Mounts & Pets"
        return "Misc`Other"
    return "Misc`Other"


def read_state():
    db = lua_table.parse(SV.read_text(errors="replace"))["TradeSkillMasterDB"]
    return (set(db["p@Default@userData@groups"]),
            {int(k[2:]): v for k, v in db["p@Default@userData@items"].items()})


def audit(conn):
    groups, items = read_state()
    listed = {r[0] for r in conn.execute("SELECT DISTINCT item_id FROM api_auction")}
    listed |= {r[0] for r in conn.execute("SELECT DISTINCT item_id FROM api_commodity")}
    rows = conn.execute("SELECT id,name,class_id,sub_class,quality,bonding FROM item").fetchall()
    missing, wanted, untradeable = [], {}, 0
    for r in rows:
        if r["id"] in items:
            continue
        sub = r["sub_class"] if r["sub_class"] is not None else -1
        path = target(r["class_id"], sub, r["quality"], r["bonding"])
        if path is None:
            untradeable += 1
            continue
        # quest objects and class books are not auctionable; keep the ones that actually trade
        if (r["class_id"] in (12, 13) or (r["class_id"] == 9 and sub == 0)) and r["id"] not in listed:
            untradeable += 1
            continue
        missing.append(r)
        wanted[r["id"]] = path
    return {"items": len(rows), "grouped": len(items), "groups": len(groups), "missing": len(missing),
            "soulbound_skipped": untradeable, "wanted": wanted,
            "listed_missing": sum(1 for r in missing if r["id"] in listed)}


def apply(conn, write=True):
    state = audit(conn)
    _groups, items = read_state()
    wanted = {i: p for i, p in state["wanted"].items() if i not in items}
    new_groups = sorted({p for p in wanted.values() if p not in _groups})
    if not write or not wanted:
        return state, new_groups, 0
    backup = SV.with_suffix(".lua.hermes-backup")
    shutil.copy2(SV, backup)
    text = SV.read_bytes().decode("latin-1")
    nl = "\r\n" if "\r\n" in text else "\n"

    def insert(mark, lines):
        nonlocal text
        i = text.index(mark)
        j = text.index(nl, i) + len(nl)
        text = text[:j] + "".join(lines) + text[j:]

    insert(GROUPS_MARK, [l for p in new_groups for l in (f'["{p}"] = {{', "},", nl)])
    insert(ITEMS_MARK, [f'["i:{i}"] = "{p}",' + nl for i, p in sorted(wanted.items())])
    SV.write_bytes(text.encode("latin-1"))
    return state, new_groups, len(wanted)
