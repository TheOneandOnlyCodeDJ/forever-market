"""Retention for price_history: hourly for a week, daily for a quarter, nothing older."""
import datetime as dt

HOURLY_DAYS = 7
DAILY_DAYS = 90


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
    delete = [r["rid"] for r in rows if r["rid"] not in keep_daily and r["rid"] not in set(keep_hourly)]
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
