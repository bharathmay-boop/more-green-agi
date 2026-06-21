"""DB access. One seam, two drivers.

`DATABASE_URL` set  → Postgres via psycopg (prod / Neon).
`DATABASE_URL` unset → SQLite (local dev / CI), unchanged behaviour.

The Postgres path wraps the connection so the ~34 command files stay byte-for-
byte identical: SQLite `?` placeholders and `datetime('now')` are rewritten on
the fly, `with db:` maps to a transaction, and rows support BOTH `row["col"]`
and `row[0]` like `sqlite3.Row`. Prisma owns the Postgres schema, so SQLite DDL
(`CREATE TABLE`/`PRAGMA`) is a no-op on the PG path.
"""
import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from config import PROJECT_ROOT, DB_PATH, DATABASE_URL

# Dialect-neutral exception aliases so call sites can `except db.IntegrityError`
# without knowing the driver. psycopg is imported lazily — it need not be
# installed for the SQLite (local/CI) path.
if DATABASE_URL:
    import psycopg
    from psycopg.errors import IntegrityError, OperationalError
else:
    from sqlite3 import IntegrityError, OperationalError


# A SQL token is either a single-quoted literal (with '' escapes) or a bare '?'.
# Matching literals lets us leave any '?' inside them alone.
_TOKEN = re.compile(r"'(?:[^']|'')*'|\?")


@lru_cache(maxsize=2048)
def _rewrite_sql(sql: str) -> str:
    """Rewrite SQLite SQL to the psycopg dialect: `?`→`%s` (outside quoted
    literals) and `datetime('now')`→`now()`. SQL strings are static literals,
    so the cache hit rate is ~100%.  ponytail: lexer-free; a quoted literal
    containing `datetime('now')` would be wrongly rewritten — none exist."""
    sql = sql.replace("datetime('now')", "now()")
    # `INSERT OR IGNORE` → `INSERT ... ON CONFLICT DO NOTHING` (no target = any
    # unique violation, matching SQLite's semantics). `INSERT OR REPLACE` is NOT
    # handled here — it needs explicit DO UPDATE columns, so it's hand-fixed.
    if re.match(r"\s*INSERT\s+OR\s+IGNORE\b", sql, re.IGNORECASE):
        sql = re.sub(r"(\s*)INSERT\s+OR\s+IGNORE", r"\1INSERT", sql, count=1, flags=re.IGNORECASE)
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    return _TOKEN.sub(lambda m: "%s" if m.group(0) == "?" else m.group(0), sql)


class _Row:
    """Mirror of sqlite3.Row: indexable by column name AND by position, and
    dict()-convertible. Lets command code use either access style unchanged."""
    __slots__ = ("_vals", "_idx", "_cols")

    def __init__(self, cols, vals):
        self._cols = list(cols)
        self._vals = tuple(vals)
        self._idx = {c: i for i, c in enumerate(self._cols)}

    def __getitem__(self, key):
        return self._vals[self._idx[key]] if isinstance(key, str) else self._vals[key]

    def get(self, key, default=None):
        i = self._idx.get(key)
        return self._vals[i] if i is not None else default

    def keys(self):
        return list(self._cols)

    def __iter__(self):
        return iter(self._vals)  # sqlite3.Row iterates values


def _pg_row_factory(cursor):
    desc = cursor.description
    cols = [c.name for c in desc] if desc else []
    return lambda values: _Row(cols, values)


class _NullCursor:
    """Returned for DDL that Prisma already owns on Postgres."""
    lastrowid = None
    def fetchone(self): return None
    def fetchall(self): return []


_SKIP_PREFIXES = ("CREATE TABLE", "CREATE INDEX", "CREATE UNIQUE INDEX", "PRAGMA")


class _PgConn:
    """sqlite3.Connection-compatible wrapper over a psycopg connection."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        if sql.lstrip().upper().startswith(_SKIP_PREFIXES):
            # ponytail: Prisma migrations are the PG schema; inline SQLite DDL
            # is a no-op here. Drop this guard if the pipeline ever owns DDL.
            return _NullCursor()
        cur = self._conn.cursor(row_factory=_pg_row_factory)
        cur.execute(_rewrite_sql(sql), tuple(params))
        return cur

    def executemany(self, sql, seq):
        cur = self._conn.cursor()
        cur.executemany(_rewrite_sql(sql), [tuple(p) for p in seq])
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Mirror `with sqlite3_conn:` — commit on success, rollback on error.
        # NOT psycopg3's native `with conn:` (that closes the connection).
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        return False


def get_db():
    if DATABASE_URL:
        # ponytail: short-lived CLI connection; autocommit off so `with db:`
        # and explicit commit() match SQLite. Pool it if a long-running
        # process ever holds this open (idle-in-transaction otherwise).
        return _PgConn(psycopg.connect(DATABASE_URL, autocommit=False))

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
