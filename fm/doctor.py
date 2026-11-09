"""Health check: is this forever-market install wired up and fresh. Never writes anything."""
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fm import blizzard, export_tsm, paths, tsm_patch

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
TSM_API = Path(paths.CLIENT_DIR) / "Interface/AddOns/TradeSkillMaster/App/API.lua"
BRIDGE = Path(paths.CLIENT_DIR) / "Interface/AddOns/ForeverMarketBridge"
TIMERS = ("forever-market-sync.timer", "forever-market-regions.timer")


def _lines():
    return []


def _sv_dir():
    try:
        return export_tsm.target().parent
    except SystemExit:
        return None


def _age_hours(path):
    if not path or not path.exists():
        return None
    return (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 3600


def _systemctl(*args):
    try:
        out = subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def checks(conn, offline=None):
    """Return [(level, name, detail)] with level in ok/warn/fail."""
    if offline is None:
        offline = os.environ.get("FM_DOCTOR_OFFLINE") == "1"
    out = []

    def add(level, name, detail):
        out.append((level, name, detail))

    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    have_creds = bool(env.get("BLIZZARD_CLIENT_ID") and env.get("BLIZZARD_CLIENT_SECRET"))
    add("ok" if have_creds else "fail", "credentials",
        f"{ENV_PATH.name} has client id and secret" if have_creds else f"missing in {ENV_PATH}")

    if offline or not have_creds:
        add("warn", "token", "skipped")
    else:
        try:
            blizzard.token()
            add("ok", "token", "fetched and usable")
        except Exception as exc:  # noqa: BLE001 - any failure is the answer
            add("fail", "token", f"{type(exc).__name__}: {exc}")

    for name, state in tsm_patch.check():
        if state == "applied":
            add("ok", f"tsm patch {name}", "present")
        elif state == "missing":
            add("fail", f"tsm patch {name}", "TSM not installed at the expected path")
        else:
            add("fail", f"tsm patch {name}", "wiped by a TSM update, run: fm patch-tsm")

    if BRIDGE.is_dir() and (BRIDGE / "ForeverMarketBridge.toc").exists():
        add("ok", "bridge addon", str(BRIDGE.name))
    else:
        add("fail", "bridge addon", "not installed in Interface/AddOns")

    sv = _sv_dir()
    for name in ("ForeverMarketPrice.lua", "ForeverMarketData.lua"):
        path = (sv / name) if sv else None
        age = _age_hours(path)
        if age is None:
            add("fail", name, "missing")
        elif age > 26:
            add("warn", name, f"{age:.1f}h old")
        else:
            add("ok", name, f"{age:.1f}h old")
    pending = (sv / "ForeverMarketData.pending.lua") if sv else None
    if pending and pending.exists():
        add("warn", "pending export", f"waiting, {_age_hours(pending):.1f}h old")
    else:
        add("ok", "pending export", "none")

    for timer in TIMERS:
        state = _systemctl("is-active", timer)
        if state is None:
            add("warn", timer, "systemctl unavailable")
            continue
        nxt = _systemctl("show", "-p", "NextElapseUSecRealtime", "--value", timer)
        add("ok" if state == "active" else "fail", timer, f"{state}, next {nxt or '-'}")

    for source in ("tsm", "api"):
        r = conn.execute("SELECT MAX(at) FROM price_history WHERE source = ?", (source,)).fetchone()
        if not r or not r[0]:
            add("fail", f"price {source}", "no history")
            continue
        age = (datetime.now(timezone.utc)
               - datetime.fromisoformat(r[0].replace("Z", "+00:00"))).total_seconds() / 3600
        add("ok" if age <= 3 else "warn", f"price {source}", f"latest snapshot {age:.1f}h old")

    for table in ("item", "price_realm", "price_history", "api_auction"):
        n = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        add("ok", f"rows {table}", str(n))
    return out


def run(conn, offline=None):
    results = checks(conn, offline=offline)
    for level, name, detail in results:
        print(f"{level:<4} {name:<22} {detail}")
    failed = sum(1 for level, _, _ in results if level == "fail")
    print(f"\n{len(results)} checks, {failed} failing")
    return 1 if failed else 0
