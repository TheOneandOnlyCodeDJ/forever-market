"""LootTrackerForever SavedVariables -> loot_session / loot_source / loot_item_source / loot_item."""
from pathlib import Path

from fm import lua_table, paths

GLOB = "WTF/Account/*/*/*/SavedVariables/LootTrackerForever.lua"
UPSERT = """INSERT INTO loot_session VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET ended = excluded.ended, kills = excluded.kills,
              loots = COALESCE(excluded.loots, loots), copper = excluded.copper,
              seconds = excluded.seconds, imported_at = excluded.imported_at"""


def _secs(v):
    return None if v is None else round(v)


def sessions(path):
    """One file -> list of (session row, sources, item_sources, items); history entries have no children."""
    character = Path(path).parts[-3]
    data = lua_table.parse(Path(path).read_text())["LootTrackerForeverData"]
    out = []
    for h in data.get("history") or []:
        if h.get("started") is None:
            continue  # no stable id without a start time
        out.append(((f"{character}:{h['started']}", character, h["started"], h.get("ended"), h.get("kills"),
                     None, h.get("copper"), _secs(h.get("seconds", h.get("elapsed")))), None, None, None))
    s = data.get("session") or {}
    if s.get("started") is not None:
        sid = f"{character}:{s['started']}"
        src = s.get("sources") or {}
        sources = [(sid, name, v.get("kills"), v.get("copper")) for name, v in src.items()]
        item_sources = [(sid, name, int(item), n) for name, v in src.items()
                        for item, n in (v.get("items") or {}).items()]
        items = [(sid, int(item), v.get("count"), v.get("vendor"), v.get("name"), v.get("q"))
                 for item, v in (s.get("items") or {}).items()]
        out.append(((sid, character, s["started"], None, s.get("kills"), s.get("loots"), s.get("copper"),
                     _secs(s.get("elapsed"))), sources, item_sources, items))
    return character, out


def run(conn, client_dir=paths.CLIENT_DIR, dry_run=False):
    files = sorted(Path(client_dir).glob(GLOB))
    if not files:
        print(f"no LootTrackerForever.lua under {client_dir}")
    for f in files:
        character, found = sessions(f)
        live = [x for x in found if x[1] is not None]
        sources, item_sources, items = (sum((x[i] for x in live), []) for i in (1, 2, 3))
        kills = sum(x[0][4] or 0 for x in found)
        line = (f"{character}: sessions {len(found)}, kills {kills}, sources {len(sources)}, "
                f"items {len(items)}")
        src_kills = {(sid, name): k for sid, name, k, _ in sources}
        rates = [(n / src_kills[(sid, name)], n, src_kills[(sid, name)], item, name)
                 for sid, name, item, n in item_sources if (src_kills.get((sid, name)) or 0) >= 20]
        if rates:
            r, n, k, item, name = max(rates)
            item_name = {i: nm for _, i, _, _, nm, _ in items}.get(item) or f"item {item}"
            line += f", best rate {100 * r:.1f}% {item_name} from {name} ({n}/{k} kills)"
        print(line)
        if dry_run:
            continue
        for row, src, item_src, its in found:
            conn.execute(UPSERT, row)
            if src is None:
                continue  # history: keep any per-source detail stored while it was the live session
            for t in ("loot_source", "loot_item_source", "loot_item"):
                conn.execute(f"DELETE FROM {t} WHERE session_id = ?", (row[0],))
            conn.executemany("INSERT INTO loot_source VALUES (?, ?, ?, ?)", src)
            conn.executemany("INSERT INTO loot_item_source VALUES (?, ?, ?, ?)", item_src)
            conn.executemany("INSERT INTO loot_item VALUES (?, ?, ?, ?, ?, ?)", its)
    if not dry_run:
        conn.commit()
    return files
