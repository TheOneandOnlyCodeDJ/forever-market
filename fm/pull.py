"""Pull the addon data published by the hourly cloud sync onto this machine.

The local timer writes the same files, but it only runs while the PC is on. The cloud job keeps
them current, so this fetches whatever it produced and only touches the disk when the bytes
actually differ.

Merging matters: the cloud database is young, so its Data.lua carries a handful of points per
item while the local file carries a week. Replacing one with the other is how you log in to
missing history, so by default the two are merged by timestamp and nothing is thrown away.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from fm import export_addon, lua_table, paths

DEFAULT_BASE = "https://raw.githubusercontent.com/TheOneandOnlyCodeDJ/forever-market/data"
ADDONS = "Interface/AddOns/ForeverMarketUI/Data.lua"
BRIDGE = "Interface/AddOns/ForeverMarketBridge/Data.lua"


def targets():
    base = os.environ.get("FM_PUBLISH_BASE", DEFAULT_BASE).rstrip("/")
    return [(f"{base}/Data.lua", Path(paths.CLIENT_DIR) / ADDONS, "series"),
            (f"{base}/Bridge.lua", Path(paths.CLIENT_DIR) / BRIDGE, "prices")]


STATE = Path(os.environ.get("FM_PULL_STATE", Path.home() / ".cache/fm/pull.json"))


def _state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def _save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))


def _get(url, timeout=60):
    """(bytes or None when unchanged, etag). Asking with If-None-Match keeps the frequent
    on-launch checks from re-downloading four megabytes every time."""
    state = _state()
    headers = {"User-Agent": "forever-market pull"}
    if state.get(url):
        headers["If-None-Match"] = state[url]
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            state[url] = r.headers.get("ETag") or ""
            _save_state(state)
            return body, state[url]
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return None, state.get(url, "")
        raise


def merge_series(local_text, cloud_text):
    """Union of both files, point by point. The cloud wins on a shared timestamp because it may
    hold a fresher price for that hour; the local file keeps every hour the cloud never saw."""
    local = lua_table.parse(local_text).get("ForeverMarketData") or {}
    cloud = lua_table.parse(cloud_text).get("ForeverMarketData") or {}
    out = dict(local)
    out["items"] = {k: dict(v) for k, v in (local.get("items") or {}).items()}
    added = 0
    for key, citem in (cloud.get("items") or {}).items():
        litem = out["items"].get(key)
        if not litem:
            out["items"][key] = citem
            added += 1
            continue
        by_t = {p["t"]: p for p in (litem.get("series") or []) if isinstance(p, dict) and "t" in p}
        before = len(by_t)
        for p in citem.get("series") or []:
            if isinstance(p, dict) and "t" in p:
                by_t[p["t"]] = p
        added += len(by_t) - before
        merged = dict(litem)
        merged["series"] = [by_t[t] for t in sorted(by_t)]
        for k in ("c", "s", "my"):        # fresher scalars from the cloud
            if citem.get(k) is not None:
                merged[k] = citem[k]
        out["items"][key] = merged
    stamps = [x for x in (local.get("generated_ts"), cloud.get("generated_ts")) if x]
    if stamps:
        out["generated_ts"] = max(stamps)
        out["next_update"] = max(stamps) + 3600
    return export_addon.to_lua(out), len(out["items"]), added


def merge_prices(local_text, cloud_text):
    """The bridge file is a flat table keyed "i:<id>", so there is no items subtable to merge."""
    local = lua_table.parse(local_text).get("ForeverMarketPrice") or {}
    cloud = lua_table.parse(cloud_text).get("ForeverMarketPrice") or {}
    rows = {k: v for k, v in local.items() if isinstance(v, dict)}
    before = len(rows)
    rows.update({k: v for k, v in cloud.items() if isinstance(v, dict)})
    text = ("ForeverMarketPrice={\n"
            + "".join(f"[{export_addon.lua(k)}]={export_addon.lua(v)},\n" for k, v in rows.items())
            + "}\n")
    return text, len(rows), len(rows) - before


def pull(write=True, max_age_h=0.0, force=False, merge=True):
    """[(name, status, bytes)]. max_age_h=0 checks the cloud every time, which is safe because a
    merge never drops what the local file already has."""
    out = []
    now = time.time()
    for url, dest, kind in targets():
        if (write and not force and max_age_h and dest.exists()
                and (now - dest.stat().st_mtime) < max_age_h * 3600):
            out.append((dest.name, "local is fresh", dest.stat().st_size))
            continue
        try:
            body, _etag = _get(url)
        except urllib.error.HTTPError as e:
            out.append((dest.name, f"failed: HTTP {e.code}", 0))
            continue
        except Exception as e:  # offline, DNS, timeout
            out.append((dest.name, f"failed: {type(e).__name__}", 0))
            continue
        if body is None:
            out.append((dest.name, "cloud unchanged", dest.stat().st_size if dest.exists() else 0))
            continue
        if dest.exists() and merge:
            try:
                text, n, extra = (merge_series if kind == "series" else merge_prices)(
                    dest.read_text(encoding="utf-8", errors="replace"), body.decode("utf-8", "replace"))
            except Exception as e:
                out.append((dest.name, f"merge failed: {type(e).__name__}", 0))
                continue
            if write:
                dest.write_text(text, encoding="utf-8")
            out.append((dest.name, f"merged, {n} items, +{extra} new points" if kind == "series"
                        else f"merged, {n} priced items", len(text.encode())))
            continue
        if dest.exists() and dest.read_bytes() == body:
            out.append((dest.name, "current", len(body)))
            continue
        if write:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
        out.append((dest.name, "written" if write else "would write", len(body)))
    return out


def run(write=True, max_age_h=0.0, force=False, merge=True):
    rows = pull(write, max_age_h=max_age_h, force=force, merge=merge)
    for name, status, size in rows:
        print(f"pull {name}: {status}" + (f" ({size:,} bytes)" if size else ""))
    return 0 if all(not s.startswith("failed") and not s.startswith("merge failed")
                    for _, s, _ in rows) else 1
