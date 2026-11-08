"""Official Blizzard API for WoW Forever: OAuth token, JSON GET, house sync. Shapes are provisional."""
import base64
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from fm import db, http
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


def store_house(conn, ruleset, house_id, name, payload, commodities, captured_at):
    """Replace one house's rows wholesale."""
    auctions = auction_rows(house_id, payload, captured_at)
    comm = commodity_rows(house_id, commodities, captured_at)
    conn.execute("DELETE FROM api_auction WHERE house_id = ?", (house_id,))
    conn.execute("DELETE FROM api_commodity WHERE house_id = ?", (house_id,))
    conn.executemany("INSERT OR REPLACE INTO api_auction VALUES (?,?,?,?,?,?,?,?,?)", auctions)
    conn.executemany("INSERT INTO api_commodity VALUES (?,?,?,?,?)", comm)
    conn.execute("INSERT OR REPLACE INTO api_house VALUES (?,?,?,?,?,?,?)",
                 (house_id, ruleset, name, faction(name), len(auctions), len(comm), captured_at))
    conn.commit()
    return auctions, comm


def probe(ruleset=1, region=None, get=get):
    for rid, name in rulesets(get("/data/wow/ruleset/index", region=region)):
        print(f"ruleset {rid}: {name}")
    rs = get(f"/data/wow/ruleset/{ruleset}", region=region)
    print(f"ruleset {ruleset} detail: name={_name(rs.get('name'))} status={rs.get('status')} "
          f"auctions={rs.get('auctions')}")
    for hid, name in houses(get(house_path(ruleset), region=region)):
        print(f"house {hid}: {name}")


def sync(conn, ruleset=1, which="horde", region=None, get=get):
    get(f"/data/wow/ruleset/{ruleset}", region=region)  # fail fast on a bad ruleset
    kept = [(hid, name) for hid, name in houses(get(house_path(ruleset), region=region))
            if which == "all" or "Horde" in name or "Blackwater" in name]
    known = {r[0] for r in conn.execute("SELECT id FROM item")}
    ids, n_auctions, n_comm = set(), 0, 0
    for hid, name in kept:
        payload = get(house_path(ruleset, hid), region=region)
        try:
            comm = get(house_path(ruleset, hid, commodities=True), region=region).get("auctions")
        except BlizzardError as e:
            print(f"house {hid}: commodities endpoint failed ({e}), using inline commodities")
            comm = payload.get("commodities")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        auctions, comm_rows = store_house(conn, ruleset, hid, name, payload, comm, now)
        n_auctions += len(auctions)
        n_comm += len(comm_rows)
        ids |= {r[2] for r in auctions if r[2] is not None} | {r[1] for r in comm_rows if r[1] is not None}
    missing = len(ids - known)
    print(f"houses fetched: {len(kept)}, auctions: {n_auctions}, commodities: {n_comm}, "
          f"distinct item ids: {len(ids)}, ids missing from item: {missing}")
    db.log_sync(conn, "blizzard api", n_auctions + n_comm,
                f"ruleset {ruleset}, {len(kept)} houses, {missing} ids not in item")
    return {"houses": len(kept), "auctions": n_auctions, "commodities": n_comm, "ids": len(ids), "missing": missing}
