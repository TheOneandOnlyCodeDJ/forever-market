"""Write addon data files straight into the addon folders.

SavedVariables are the wrong channel for hourly data: the client rewrites them from memory on
logout and on /reload, so anything written during a session is lost. Addon Lua files are never
touched by the client, and /reload re-reads them from disk. So the exporters write Data.lua next
to the addon instead, and the user only has to /reload.
"""
from pathlib import Path

from fm import paths


def path(addon, filename="Data.lua", client_dir=paths.CLIENT_DIR):
    return Path(client_dir) / "Interface" / "AddOns" / addon / filename


def write(target, text):
    """Atomic: a half written file would be a Lua syntax error at /reload."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)
    return target
