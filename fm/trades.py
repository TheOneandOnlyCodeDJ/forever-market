"""Import TSM Accounting's own transaction log (real bought-at / sold-at prices).

TSM keeps two CSV strings in SavedVariables:
  r@<realm>@internalData@csvSales  and  csvBuys
columns: itemString,stackSize,quantity,price,otherPlayer,player,time,source
`price` is the total for the transaction, so the unit price is price / quantity.
"""
import re
from pathlib import Path

from fm import paths

SV = Path(paths.CLIENT_DIR) / "WTF/Account"


def _accounts():
    return sorted(SV.glob("*/SavedVariables/TradeSkillMaster.lua"))


def _csv_field(text, key):
    """Pull one `["key"] = "..."` Lua string out without running a Lua interpreter."""
    m = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*"((?:[^"\\]|\\.)*)"', text)
    if not m:
        return ""
    return m.group(1).replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def parse(text):
    """[(at, kind, item_id, stack, qty, total, unit, other, player, source)] from a SavedVariables file."""
    rows = []
    for kind, field in (("sale", "csvSales"), ("buy", "csvBuys")):
        for k in re.findall(r'\["(r@[^"]*@internalData@' + field + r')"\]', text):
            block = _csv_field(text, k)
            for line in block.splitlines()[1:]:  # first line is the header
                parts = line.split(",")
                if len(parts) < 8:
                    continue
                item_string, stack, qty, price, other, player, when, source = parts[:8]
                m = re.match(r"i:(\d+)", item_string)
                if not m:
                    continue
                try:
                    qty_i, total = int(qty), int(price)
                    at = int(when)
                except ValueError:
                    continue
                rows.append((at, kind, int(m.group(1)), int(stack or 0), qty_i, total,
                             total // qty_i if qty_i else None, other, player, source))
    return rows


def run(conn, files=None):
    files = files or _accounts()
    if not files:
        print(f"no TradeSkillMaster SavedVariables under {SV}")
        return 1
    total, inserted = 0, 0
    for path in files:
        rows = parse(path.read_text(errors="replace"))
        total += len(rows)
        for r in rows:
            cur = conn.execute("INSERT OR IGNORE INTO trade VALUES (?,?,?,?,?,?,?,?,?,?)", r)
            inserted += cur.rowcount
    conn.commit()
    print(f"tsm trades: {total} rows parsed from {len(files)} account(s), {inserted} new")
    return 0


def summary(conn, item_id):
    """(sales_count, avg_unit_price, last_sale_at) for one item, or None."""
    r = conn.execute("""SELECT COUNT(*), AVG(unit), MAX(at) FROM trade WHERE kind = 'sale' AND item_id = ?""",
                     (item_id,)).fetchone()
    return (r[0], r[1], r[2]) if r and r[0] else None
