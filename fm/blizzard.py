"""Official Blizzard API for WoW Forever: OAuth token, JSON GET, house sync. Shapes are provisional."""
import base64
import json
import os
import statistics
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from fm import auction_life, db, history, http
from fm.db import ROOT

ENV_PATH = ROOT / ".env"
TOKEN_PATH = ROOT / "data" / "cache" / "blizzard_token.json"
TOKEN_URL = "https://oauth.battle.net/token"
REGIONS = ("us", "eu", "kr", "tw")


class BlizzardError(Exception):
    def __init__(self, status, body):
        self.status = status
        snippet = body[:200].decode("utf-8", "replace") if isinstance(body, bytes) else str(body)[:200]
        super().__init__(f"HTTP {status}: {snippet}")


class MissingCredentials(Exception):
    pass


def transport(url, data=None, headers=None):
    return http.request(url, data, headers, delay=0.2)


def credentials():
    """(client_id, secret, region) from the environment, else `.env`."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.strip().startswith("#"):
                env[key.strip()] = value.strip().strip("'\"")
    val = lambda k: os.environ.get(k) or env.get(k)
    cid, secret = val("BLIZZARD_CLIENT_ID"), val("BLIZZARD_CLIENT_SECRET")
    if not (cid and secret):
        raise MissingCredentials("no Blizzard credentials: set BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET in .env")
    return cid, secret, val("BLIZZARD_REGION") or "us"


def token(transport=transport, now=time.time):
    """Bearer token, reused from TOKEN_PATH until 120 s before expiry."""
    cid, secret, _ = credentials()
    try:
        cached = json.loads(TOKEN_PATH.read_text())
        if cached["expires_at"] - 120 > now():
            return cached["access_token"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    status, body = transport(TOKEN_URL, data=b"grant_type=client_credentials",
                             headers={"Authorization": f"Basic {auth}",
                                      "Content-Type": "application/x-www-form-urlencoded"})
    if status != 200:
        raise BlizzardError(status, body)
    try:
        payload = json.loads(body)
        tok, expires_at = payload["access_token"], now() + int(payload["expires_in"])
    except (ValueError, KeyError, TypeError):
        raise BlizzardError(status, body) from None
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps({"access_token": tok, "expires_at": expires_at}))
    TOKEN_PATH.chmod(0o600)
    return tok


def get(path, namespace=None, region=None, transport=transport):
    region = region or credentials()[2]
    if region not in REGIONS:
        raise BlizzardError(None, f"unknown region {region!r}, expected one of {', '.join(REGIONS)}")
    url = f"https://{region}.api.blizzard.com{path}?" + urlencode(
        {"namespace": namespace or f"dynamic-forever-{region}"})
    status, body = transport(url, headers={"Authorization": f"Bearer {token(transport)}",
                                           "Accept-Encoding": "gzip"})
    if status != 200:
        raise BlizzardError(status, body)
    try:
        return json.loads(body)
    except ValueError:
        raise BlizzardError(status, body) from None


def _name(v):
    """Names may come back as a string or a {locale: string} map."""
    return v.get("en_US") or next(iter(v.values()), None) if isinstance(v, dict) else v


def rulesets(index):
    return [(r.get("id"), _name(r.get("name"))) for r in index.get("rulesets") or []]


def house_path(ruleset, house=None, commodities=False):
    """The house index needs its trailing slash: `/auctions/`."""
    return f"/data/wow/ruleset/{ruleset}/auctions/{'' if house is None else house}" + (
        "/commodities" if commodities else "")


def houses(index):
    return [(h["id"], _name(h.get("name")) or "") for h in index.get("auctions") or [] if h.get("id") is not None]


def faction(name):
    return next((f for f in ("Alliance", "Horde", "Blackwater") if f in name), None)


def auction_rows(house_id, payload, captured_at):
    """`auctions` is optional: some houses omit it entirely."""
    return [(house_id, a.get("id"), (a.get("item") or {}).get("id"), a.get("quantity"), a.get("buyout"),
             a.get("bid"), a.get("unit_price"), a.get("time_left"), captured_at)
            for a in payload.get("auctions") or [] if a.get("id") is not None]


def commodity_rows(house_id, entries, captured_at):
    return [(house_id, (c.get("item") or {}).get("id"), c.get("quantity"), c.get("unit_price"), captured_at)
            for c in entries or []]


def store_house(conn, ruleset, house_id, name, payload, commodities, captured_at, region="us"):
    """Replace one house's rows wholesale."""
    auctions = auction_rows(house_id, payload, captured_at)
    comm = commodity_rows(house_id, commodities, captured_at)
    conn.execute("DELETE FROM api_auction WHERE house_id = ?", (house_id,))
    conn.execute("DELETE FROM api_commodity WHERE house_id = ?", (house_id,))
    conn.executemany("INSERT OR REPLACE INTO api_auction VALUES (?,?,?,?,?,?,?,?,?)", auctions)
    conn.executemany("INSERT INTO api_commodity VALUES (?,?,?,?,?)", comm)
    conn.execute("INSERT OR REPLACE INTO api_house VALUES (?,?,?,?,?,?,?,?)",
                 (house_id, ruleset, name, faction(name), len(auctions), len(comm), captured_at, region))
    conn.commit()
    return auctions, comm


def probe(ruleset=1, region=None, get=get):
    # the live index carries only `key` and `id` per ruleset, no name
    for rid, name in rulesets(get("/data/wow/ruleset/index", region=region)):
        print(f"ruleset {rid}: {name or '-'}")
    rs = get(f"/data/wow/ruleset/{ruleset}", region=region)
    print(f"ruleset {ruleset} detail: name={_name(rs.get('name')) or '-'} status={rs.get('status')} "
          f"auctions={rs.get('auctions')}")
    for hid, name in houses(get(house_path(ruleset), region=region)):
        print(f"house {hid}: {name}")


def score(pairs):
    """[(api unit minBO, tsm minBO)] -> (common, exact within 1 copper, median relative difference)."""
    pairs = [(a, t) for a, t in pairs if a and t]
    if not pairs:
        return 0, 0, None
    return (len(pairs), sum(abs(a - t) <= 1 for a, t in pairs),
            statistics.median(abs(a - t) / t for a, t in pairs))


def match(conn):
    """Score every house with auctions against price_realm.min_buyout, persist, return best first."""
    pairs = {}
    for hid, a, t in conn.execute("""SELECT a.house_id, MIN(a.buyout / a.quantity), p.min_buyout
            FROM api_auction a JOIN price_realm p ON p.item_id = a.item_id
            WHERE a.buyout > 0 AND a.quantity > 0 AND p.min_buyout > 0 GROUP BY a.house_id, a.item_id"""):
        pairs.setdefault(hid, []).append((a, t))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = [(hid, *score(p), now) for hid, p in pairs.items()]
    rows.sort(key=lambda r: (-r[2] / r[1], r[3], r[0]))
    conn.execute("DELETE FROM api_house_match")
    conn.executemany("INSERT INTO api_house_match VALUES (?,?,?,?,?)", rows)
    conn.commit()
    return rows


def print_match(rows):
    print(f"{'house':>6} {'common':>7} {'exact':>6} {'exact %':>8} {'median diff':>12}")
    for hid, common, exact, med, _ in rows:
        print(f"{hid:>6} {common:>7} {exact:>6} {100 * exact / common:>7.1f}% {med:>12.2f}")
    best = next((r[0] for r in rows if r[1] >= 50), None)
    print(f"recommended house: {best if best is not None else '-'}")


def home_region():
    try:
        return credentials()[2]
    except MissingCredentials:
        return "us"


def sync(conn, ruleset=1, which="horde", region=None, get=get, house=None):
    """Every fetched house gets a price_history snapshot. Only the home region lands in the api_* tables:
    house ids repeat across regions, so a foreign house would overwrite the home one."""
    home = home_region()
    region = region or home
    get(f"/data/wow/ruleset/{ruleset}", region=region)  # fail fast on a bad ruleset
    kept = [(hid, name) for hid, name in houses(get(house_path(ruleset), region=region))
            if hid == house or house is None and (which == "all" or "Horde" in name or "Blackwater" in name)]
    if house is not None and not kept:
        raise BlizzardError(None, f"house {house} not in ruleset {ruleset} index")
    known = {r[0] for r in conn.execute("SELECT id FROM item")}
    ids, n_auctions, n_comm = set(), 0, 0
    life_totals = {}
    for hid, name in kept:
        payload = get(house_path(ruleset, hid), region=region)
        try:
            comm = get(house_path(ruleset, hid, commodities=True), region=region).get("auctions")
        except BlizzardError as e:
            print(f"house {hid}: commodities endpoint failed ({e}), using inline commodities")
            comm = payload.get("commodities")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if region == home:
            auctions, comm_rows = store_house(conn, ruleset, hid, name, payload, comm, now, region)
        else:
            auctions, comm_rows = auction_rows(hid, payload, now), commodity_rows(hid, comm, now)
        if region == home:
            life = auction_life.track(conn, hid, auctions)
            life_totals = {k: life_totals.get(k, 0) + v for k, v in life.items()}
        history.append(conn, history.hour(), "api", region, hid, history.api_rows(auctions, comm_rows))
        n_auctions += len(auctions)
        n_comm += len(comm_rows)
        ids |= {r[2] for r in auctions if r[2] is not None} | {r[1] for r in comm_rows if r[1] is not None}
    missing = len(ids - known)
    print(f"{region}: houses fetched: {len(kept)}, auctions: {n_auctions}, commodities: {n_comm}, "
          f"distinct item ids: {len(ids)}, ids missing from item: {missing}")
    if life_totals:
        print(f"auction life: new {life_totals.get('new', 0)}, still listed {life_totals.get('seen', 0)}, "
              f"gone {life_totals.get('gone', 0)}, inferred sold {life_totals.get('sold', 0)}")
    db.log_sync(conn, "blizzard api", n_auctions + n_comm,
                f"{region}, ruleset {ruleset}, {len(kept)} houses, {missing} ids not in item")
    return {"houses": len(kept), "auctions": n_auctions, "commodities": n_comm, "ids": len(ids), "missing": missing}
