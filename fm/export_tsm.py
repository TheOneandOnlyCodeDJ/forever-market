"""API prices of the matched house -> WTF/Account/<acct>/SavedVariables/ForeverMarketPrice.lua for the bridge addon."""
import os
import subprocess
from pathlib import Path

from fm import paths, report

FILE = "ForeverMarketPrice.lua"


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
    return out


def to_lua(data):
    lines = ["ForeverMarketPrice = {"]
    for item_id in sorted(data):
        fields = ", ".join(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}" for k, v in data[item_id].items())
        lines.append(f'  ["i:{item_id}"] = {{ {fields} }},')
    return "\n".join(lines + ["}", ""])


def target(client_dir=paths.CLIENT_DIR):
    accounts = sorted(Path(client_dir).glob("WTF/Account/*/SavedVariables"))
    if len(accounts) != 1:
        raise SystemExit(f"expected one account under {client_dir}/WTF/Account, found {len(accounts)}")
    return accounts[0] / FILE


def game_running():
    if os.environ.get("FM_SKIP_PGRP") == "1":
        return False
    return subprocess.run(["pgrep", "-x", "Wow.exe"], capture_output=True).returncode == 0


def run(conn, client_dir=paths.CLIENT_DIR):
    if game_running():
        print("Wow.exe is running; exit the game before exporting (it rewrites SavedVariables on logout)")
        return 3
    path = target(client_dir)
    data = rows(conn)
    path.write_text(to_lua(data))
    print(f"rows {len(data)} -> {path}")
    return 0
