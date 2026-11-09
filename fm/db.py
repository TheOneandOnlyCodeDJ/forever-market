import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "market.db"
SCHEMA = Path(__file__).with_name("schema.sql")


def connect(path=DB_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA.read_text())
    if "region" not in [r[1] for r in conn.execute("PRAGMA table_info(api_house)")]:
        conn.execute("ALTER TABLE api_house ADD COLUMN region TEXT DEFAULT 'us'")  # the default backfills
    return conn


def log_sync(conn, source, rows, note):
    conn.execute("INSERT INTO sync_log VALUES (?, datetime('now'), ?, ?)", (source, rows, note))
    conn.commit()
