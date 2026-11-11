"""Retention: price_history hourly for a week, daily for a quarter; auction ids for a day."""
import datetime as dt

HOURLY_DAYS = 7
DAILY_DAYS = 90
# An auction id only earns its keep while it can still be compared with the next snapshot.
# Its proof of a sale is rolled into sold_hour before the row goes.
LIFE_HOURS = 24
LIFE_STALE_DAYS = 7


def _cutoffs(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    return (now - dt.timedelta(days=HOURLY_DAYS), now - dt.timedelta(days=DAILY_DAYS))


def plan(conn, now=None):
    """Return (delete_ids, counts by bucket) without touching the table."""
    hourly_cut, daily_cut = _cutoffs(now)
    rows = conn.execute(
        "SELECT rowid AS rid, at, source, region, house_id, item_id FROM price_history ORDER BY at"
    ).fetchall()
    keep_hourly = []
    daily = {}
    old = []
    for r in rows:
        at = dt.datetime.fromisoformat(r["at"].replace("Z", "+00:00"))
        if at >= hourly_cut:
            keep_hourly.append(r["rid"])
        elif at >= daily_cut:
            key = (at.strftime("%Y-%m-%d"), r["source"], r["region"], r["house_id"], r["item_id"])
            daily[key] = r["rid"]  # later rows overwrite, so the last of the day survives
        else:
            old.append(r["rid"])
    keep_daily = set(daily.values())
    hourly = set(keep_hourly)  # hoisted: rebuilding this per row made the plan quadratic
    delete = [r["rid"] for r in rows if r["rid"] not in keep_daily and r["rid"] not in hourly]
    return delete, {"hourly": len(keep_hourly), "daily": len(keep_daily), "deleted": len(delete),
                    "total": len(rows)}


def run(conn, now=None, dry_run=False):
    delete, stats = plan(conn, now)
    if not dry_run and delete:
        # sqlite has a variable limit; delete in chunks
        for i in range(0, len(delete), 500):
            chunk = delete[i:i + 500]
            conn.execute(
                f"DELETE FROM price_history WHERE rowid IN ({','.join('?' * len(chunk))})", chunk
            )
        conn.commit()
    return stats


def plan_life(conn, now=None):
    """Rows to delete from auction_life, plus the sold totals they stand for."""
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = (now - dt.timedelta(hours=LIFE_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale = (now - dt.timedelta(days=LIFE_STALE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = conn.execute(
        """SELECT rowid AS rid, item_id, quantity, buyout, gone_at, sold, last_seen FROM auction_life
           WHERE (gone_at IS NOT NULL AND gone_at < ?) OR (gone_at IS NULL AND last_seen < ?)""",
        (cutoff, stale)).fetchall()
    totals = {}
    for r in rows:
        if not r["gone_at"] or not r["sold"]:
            continue
        key = (r["gone_at"][:13] + ":00:00Z", r["item_id"])
        t = totals.setdefault(key, [0, 0, 0])
        t[0] += r["quantity"] or 0
        t[1] += r["buyout"] or 0
        t[2] += 1
    return [r["rid"] for r in rows], totals


def run_life(conn, now=None, dry_run=False):
    delete, totals = plan_life(conn, now)
    if not dry_run and delete:
        conn.executemany(
            """INSERT INTO sold_hour (at, item_id, sold_qty, sold_copper, gone_count) VALUES (?,?,?,?,?)
               ON CONFLICT(at, item_id) DO UPDATE SET
                 sold_qty = sold_qty + excluded.sold_qty,
                 sold_copper = sold_copper + excluded.sold_copper,
                 gone_count = gone_count + excluded.gone_count""",
            [(at, item, v[0], v[1], v[2]) for (at, item), v in totals.items()])
        for i in range(0, len(delete), 500):
            chunk = delete[i:i + 500]
            conn.execute(f"DELETE FROM auction_life WHERE rowid IN ({','.join('?' * len(chunk))})", chunk)
        conn.commit()
    return {"auction_rows": len(delete), "sold_hours": len(totals)}
