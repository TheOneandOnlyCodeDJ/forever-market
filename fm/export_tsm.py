"""API prices of the matched house -> the bridge addon's Data.lua (never SavedVariables)."""
import os
import subprocess
from pathlib import Path

from fm import addon_files, paths, report

ADDON = "ForeverMarketBridge"


def rows(conn):
    """{item_id: {minbo, qty, listings, market?, value?, at}} for items with api auctions on the picked house."""
    house, _ = report.pick_house(conn)
    out = {}
    for r in conn.execute("""SELECT a.item_id, MIN(a.buyout / a.quantity), SUM(a.quantity), COUNT(*),
                                    NULLIF(p.market_value, 0), MAX(a.captured_at)
                             FROM api_auction a LEFT JOIN price_realm p ON p.item_id = a.item_id
                             WHERE a.house_id = ? AND a.buyout > 0 AND a.quantity > 0
                             GROUP BY a.item_id ORDER BY a.item_id""", (house,)):
        item_id, minbo, qty, listings, market, at = r
        d = {"minbo": minbo, "qty": qty, "listings": listings}
        if market is not None:
            d["market"] = market
        value, source = report.value_of(conn, item_id)
        if source != "none":  # "none" means unknown, not worth 0
            d["value"] = value
        d["at"] = at.replace(" ", "T") + "Z"
        out[item_id] = d
    # Commodities have no auctions, only stack listings with a unit price. Without this the bridge
    # had nothing for ore, herbs, cloth or fish, so TSM saw no prices for any trade good.
    for r in conn.execute("""SELECT c.item_id, MIN(c.unit_price), SUM(c.quantity), COUNT(*),
                                    NULLIF(p.market_value, 0), MAX(c.captured_at)
                             FROM api_commodity c LEFT JOIN price_realm p ON p.item_id = c.item_id
                             WHERE c.house_id = ? AND c.unit_price > 0 AND c.quantity > 0
                             GROUP BY c.item_id""", (house,)):
        item_id, unit, qty, listings, market, at = r
        d = {"minbo": unit, "qty": qty, "listings": listings, "kind": "commodity"}
        if market is not None:
            d["market"] = market
        value, source = report.value_of(conn, item_id)
        if source != "none":
            d["value"] = value
        d["at"] = (at or "").replace(" ", "T") + "Z"
        out.setdefault(item_id, d)
    return out


def to_lua(data):
    lines = ["ForeverMarketPrice = {"]
    for item_id in sorted(data):
        fields = ", ".join(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}" for k, v in data[item_id].items())
        lines.append(f'  ["i:{item_id}"] = {{ {fields} }},')
    return "\n".join(lines + ["}", ""])


def target(client_dir=paths.CLIENT_DIR):
    return addon_files.path(ADDON, client_dir=client_dir)


def game_running():
    if os.environ.get("FM_SKIP_PGRP") == "1":
        return False
    return subprocess.run(["pgrep", "-x", "Wow.exe"], capture_output=True).returncode == 0


def run(conn, client_dir=paths.CLIENT_DIR):
    data = rows(conn)
    path = addon_files.write(target(client_dir), to_lua(data))
    print(f"rows {len(data)} -> {path} (the game can be open; /reload picks it up)")
    return 0
