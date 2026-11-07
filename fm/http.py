"""The only module allowed to touch the network: disk cache + per-host delay + UA."""
import hashlib
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from fm.db import ROOT

CACHE_DIR = ROOT / "data" / "cache"
UA = "forever-market/0.1 (+personal market tracker)"
MIN_DELAY = 2.0  # seconds between requests to the same host
_last_hit = {}


def get(url, ttl=6 * 3600):
    """Return the body of `url` as bytes, served from cache when younger than `ttl` seconds."""
    path = CACHE_DIR / hashlib.sha1(url.encode()).hexdigest()
    if path.exists() and time.time() - path.stat().st_mtime < ttl:
        return path.read_bytes()
    host = urlparse(url).netloc
    wait = _last_hit.get(host, 0) + MIN_DELAY - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
    finally:
        _last_hit[host] = time.monotonic()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(body)
    tmp.replace(path)
    return body
