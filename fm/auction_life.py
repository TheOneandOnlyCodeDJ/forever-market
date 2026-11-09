"""Infer sales from auction ids that vanish well before their listing could expire.

The API has no sold data, so this is the closest measurable proxy: an auction seen at hour N
and gone at hour N+1 cannot have expired if its remaining duration was longer than the gap.
Only those are counted. Anything that could plausibly have timed out is recorded as gone with
sold = 0, so the estimate is conservative by construction.

`time_left` is a coarse bucket, not a timestamp, so the lower bound of each bucket is used.
"""
import datetime as dt

# conservative lower bounds in minutes for each bucket the API returns
BUCKET_MIN = {"VERY_LONG": 12 * 60, "LONG": 4 * 60, "MEDIUM": 60, "SHORT": 0}


def _ts(now):
    return now.strftime("%Y-%m-%d %H:%M:%S")


def track(conn, house_id, auctions, now=None):
    """auctions: [(house, auction_id, item_id, quantity, buyout, bid, unit_price, time_left, at)].

    Returns {"new", "seen", "gone", "sold"} counts for this house.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    stamp = _ts(now)
    rows = [a for a in auctions if a[1] is not None]
    live_ids = {a[1] for a in rows}

    existing = {r["auction_id"]: r for r in conn.execute(
        "SELECT auction_id, last_seen, time_left, gone_at FROM auction_life WHERE house_id = ?", (house_id,))}

    new = seen = 0
    for _, aid, item_id, quantity, buyout, _bid, _unit, time_left, _at in rows:
        prev = existing.get(aid)
        if prev is None:
            conn.execute(
                "INSERT OR IGNORE INTO auction_life (house_id, auction_id, item_id, quantity, buyout, time_left,"
                " first_seen, last_seen, gone_at, sold) VALUES (?,?,?,?,?,?,?,?,NULL,0)",
                (house_id, aid, item_id, quantity, buyout, time_left, stamp, stamp))
            new += 1
        elif prev["gone_at"] is None:
            conn.execute(
                "UPDATE auction_life SET last_seen = ?, time_left = ? WHERE house_id = ? AND auction_id = ?",
                (stamp, time_left, house_id, aid))
            seen += 1

    gone = sold = 0
    for aid, prev in existing.items():
        if aid in live_ids or prev["gone_at"] is not None:
            continue
        try:
            last = dt.datetime.strptime(prev["last_seen"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
        except (TypeError, ValueError):
            continue
        elapsed_min = (now - last).total_seconds() / 60
        remaining = BUCKET_MIN.get((prev["time_left"] or "").upper(), 0)
        likely_sold = 1 if remaining > elapsed_min * 1.1 else 0
        conn.execute(
            "UPDATE auction_life SET gone_at = ?, sold = ? WHERE house_id = ? AND auction_id = ?",
            (stamp, likely_sold, house_id, aid))
        gone += 1
        sold += likely_sold
    return {"new": new, "seen": seen, "gone": gone, "sold": sold}


def stats(conn, min_sold=1):
    """Per item: auctions that vanished as likely sales, quantity, and the copper that implies."""
    return conn.execute(
        """SELECT a.item_id, COALESCE(i.name, 'item ' || a.item_id) AS item,
                  COUNT(*) AS sold_auctions, SUM(a.quantity) AS sold_qty,
                  SUM(a.buyout) AS sold_copper, AVG(a.buyout * 1.0 / NULLIF(a.quantity, 0)) AS avg_unit
           FROM auction_life a LEFT JOIN item i ON i.id = a.item_id
           WHERE a.sold = 1
           GROUP BY a.item_id HAVING COUNT(*) >= ?
           ORDER BY sold_copper DESC""", (min_sold,)).fetchall()
