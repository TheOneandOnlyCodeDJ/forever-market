import csv
import io

from fm import http
from fm.db import log_sync

FOREVER = "1.60.1.70790"
ERA = "1.15.9.70576"
WAGO = "https://wago.tools/db2/{table}/csv?build={build}"
SOURCES = {
    "wago_item": ("Item", FOREVER),
    "wago_itemsparse": ("ItemSparse", FOREVER),
    "era_itemsparse": ("ItemSparse", ERA),
}


def _int(v):
    return int(v) if v not in ("", None) else None


def _fetch(source):
    table, build = SOURCES[source]
    text = http.get(WAGO.format(table=table, build=build), ttl=7 * 86400).decode("utf-8")
    return {int(r["ID"]): r for r in csv.DictReader(io.StringIO(text))}


def merge(items, forever, era):
    """Item rows supply class; ItemSparse rows (Forever over Era) supply the rest."""
    out = []
    for item_id in sorted(items.keys() | forever.keys()):
        base = items.get(item_id, {})
        if item_id in forever:
            sparse, source = forever[item_id], "forever"
        elif item_id in era:
            sparse, source = era[item_id], "era"
        else:
            sparse, source = {}, "missing"
        out.append((
            item_id, sparse.get("Display_lang") or f"item {item_id}",
            _int(sparse.get("OverallQualityID")), _int(sparse.get("ItemLevel")),
            _int(sparse.get("RequiredLevel")), _int(base.get("ClassID")),
            _int(base.get("SubclassID")), _int(sparse.get("Bonding")),
            _int(sparse.get("Stackable")), _int(sparse.get("SellPrice")), source,
        ))
    return out


def run(conn):
    failed, data = [], {}
    for source, (table, build) in SOURCES.items():
        try:
            data[source] = _fetch(source)
            log_sync(conn, source, len(data[source]), f"{table} build {build}")
            print(f"{source}: {len(data[source])} rows, build {build}")
        except Exception as e:
            data[source] = {}
            log_sync(conn, source, None, f"FAILED: {e}")
            print(f"{source}: FAILED: {e}")
            failed.append(source)
    if not (data["wago_item"] or data["wago_itemsparse"]):
        print("item: not updated (no Forever data)")
        return failed
    rows = merge(data["wago_item"], data["wago_itemsparse"], data["era_itemsparse"])
    conn.executemany("INSERT OR REPLACE INTO item VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    counts = {s: sum(r[-1] == s for r in rows) for s in ("forever", "era", "missing")}
    log_sync(conn, "item", len(rows), " ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"item: {len(rows)} rows written ({', '.join(f'{k} {v}' for k, v in counts.items())})")
    return failed
