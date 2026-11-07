import csv
import io

from fm import http
from fm.db import ROOT, log_sync

SOURCES = {
    "tsm_realm": "https://public-data.tradeskillmaster.com/forever/us/realm/pvp-horde/items.csv",
    "tsm_region": "https://public-data.tradeskillmaster.com/forever/us/region/items.csv",
}
FIXTURES = {
    "tsm_realm": ROOT / "tests" / "fixtures" / "pvp_horde_items.csv",
    "tsm_region": ROOT / "tests" / "fixtures" / "forever_us_items.csv",
}


def _int(v):
    return int(float(v)) if v not in ("", None) else None


def _float(v):
    return float(v) if v not in ("", None) else None


def ingest(conn, source, text, note=""):
    """Upsert one TSM CSV; returns (rows, updatedAt)."""
    rows = list(csv.DictReader(io.StringIO(text)))
    if source == "tsm_realm":
        conn.executemany(
            "INSERT OR REPLACE INTO price_realm VALUES (?,?,?,?,?,?)",
            [(int(r["itemId"]), _int(r["marketValue"]), _int(r["minBuyout"]), _int(r["recent"]),
              _int(r["historical"]), r["updatedAt"]) for r in rows])
    else:
        conn.executemany(
            "INSERT OR REPLACE INTO price_region VALUES (?,?,?,?,?,?,?)",
            [(int(r["itemId"]), _int(r["marketValue"]), _int(r["historical"]),
              _int(r["avgSalePrice"]), _float(r["saleRate"]), _float(r["soldPerDay"]),
              r["updatedAt"]) for r in rows])
    updated = rows[0]["updatedAt"] if rows else None
    log_sync(conn, source, len(rows), f"{updated}{note}")
    return len(rows), updated


def run(conn, fixtures=False):
    """Sync every source; a failed source is logged and skipped. Returns failed source names."""
    failed = []
    for source, url in SOURCES.items():
        try:
            text = FIXTURES[source].read_text() if fixtures else http.get(url).decode("utf-8")
            n, updated = ingest(conn, source, text, " (fixture)" if fixtures else "")
            print(f"{source}: {n} rows, updatedAt {updated}")
        except Exception as e:
            log_sync(conn, source, None, f"FAILED: {e}")
            print(f"{source}: FAILED: {e}")
            failed.append(source)
    return failed
