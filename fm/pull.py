"""Pull the addon data published by the hourly cloud sync onto this machine.

The local timer writes the same files, but it only runs while the PC is on. The cloud job keeps
them current, so this fetches whatever it produced and only touches the disk when the bytes
actually differ.
"""
from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from fm import paths

DEFAULT_BASE = "https://raw.githubusercontent.com/TheOneandOnlyCodeDJ/forever-market/data"
ADDONS = "Interface/AddOns/ForeverMarketUI/Data.lua"
BRIDGE = "Interface/AddOns/ForeverMarketBridge/Data.lua"


def targets():
    base = os.environ.get("FM_PUBLISH_BASE", DEFAULT_BASE).rstrip("/")
    return [(f"{base}/Data.lua", Path(paths.CLIENT_DIR) / ADDONS),
            (f"{base}/Bridge.lua", Path(paths.CLIENT_DIR) / BRIDGE)]


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "forever-market pull"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Last-Modified")


def pull(write=True, max_age_h=2.0, force=False):
    """[(name, status, bytes)]. A file the local timer wrote recently already carries a richer
    history than the cloud copy, so only a stale local file is replaced."""
    out = []
    now = time.time()
    for url, dest in targets():
        if (write and not force and dest.exists()
                and (now - dest.stat().st_mtime) < max_age_h * 3600):
            out.append((dest.name, "local is fresh", dest.stat().st_size))
            continue
        try:
            body, stamp = _get(url)
        except urllib.error.HTTPError as e:
            out.append((dest.name, f"failed: HTTP {e.code}", 0))
            continue
        except Exception as e:  # offline, DNS, timeout
            out.append((dest.name, f"failed: {type(e).__name__}", 0))
            continue
        if dest.exists() and dest.read_bytes() == body:
            out.append((dest.name, "current", len(body)))
            continue
        if write:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
        out.append((dest.name, "written" if write else "would write", len(body)))
        if stamp:
            out[-1] = (out[-1][0], out[-1][1], len(body))
    return out


def run(write=True, max_age_h=2.0, force=False):
    rows = pull(write, max_age_h=max_age_h, force=force)
    for name, status, size in rows:
        print(f"pull {name}: {status}" + (f" ({size:,} bytes)" if size else ""))
    return 0 if all(not s.startswith("failed") for _, s, _ in rows) else 1
