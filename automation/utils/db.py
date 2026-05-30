import sqlite3
from pathlib import Path
from config import PROJECT_ROOT, DB_PATH


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    schema = (PROJECT_ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
