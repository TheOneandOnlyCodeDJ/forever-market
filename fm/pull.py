"""Pull the addon data published by the hourly cloud sync onto this machine.

The local timer writes the same files, but it only runs while the PC is on. The cloud job keeps
them current, so this fetches whatever it produced and only touches the disk when the bytes
actually differ.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path

from fm import paths

DEFAULT_BASE = "https://raw.githubusercontent.com/TheOneandOnlyCodeDJ/forever-market/data"
ADDONS = "Interface/AddOns/ForeverMarketUI/Data.lua"
BRIDGE = "WTF/Account/250808230#1/SavedVariables/ForeverMarketPrice.lua"


def targets():
    base = os.environ.get("FM_PUBLISH_BASE", DEFAULT_BASE).rstrip("/")
    return [(f"{base}/Data.lua", Path(paths.CLIENT_DIR) / ADDONS),
            (f"{base}/ForeverMarketPrice.lua", Path(paths.CLIENT_DIR) / BRIDGE)]


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "forever-market pull"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Last-Modified")


def pull(write=True):
    """[(name, status, bytes)] where status is written/current/missing/failed: ..."""
    out = []
    for url, dest in targets():
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


def run(write=True):
    rows = pull(write)
    for name, status, size in rows:
        print(f"pull {name}: {status}" + (f" ({size:,} bytes)" if size else ""))
    return 0 if all(not s.startswith("failed") for _, s, _ in rows) else 1
