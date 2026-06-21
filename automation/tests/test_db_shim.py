"""Phase 0 — Postgres shim. The risky bit is the SQL dialect rewrite that runs
on the Postgres path: `?`→`%s` and `datetime('now')`→`now()`, WITHOUT mangling
`?` or the literal inside a quoted string. Pure-function tests, no DB needed."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from utils.db import _rewrite_sql  # noqa: E402


def test_question_mark_becomes_percent_s():
    assert _rewrite_sql("SELECT * FROM t WHERE id=?") == "SELECT * FROM t WHERE id=%s"


def test_multiple_placeholders():
    assert _rewrite_sql("INSERT INTO t VALUES(?,?,?)") == "INSERT INTO t VALUES(%s,%s,%s)"


def test_question_mark_inside_single_quotes_is_preserved():
    # The '?' in the literal must NOT become %s; the real placeholder must.
    assert (
        _rewrite_sql("SELECT * FROM t WHERE note='why?' AND id=?")
        == "SELECT * FROM t WHERE note='why?' AND id=%s"
    )


def test_datetime_now_becomes_now():
    assert (
        _rewrite_sql("UPDATE t SET updated_at=datetime('now') WHERE id=?")
        == "UPDATE t SET updated_at=now() WHERE id=%s"
    )


def test_idempotent_on_already_postgres_sql():
    # No '?' and no datetime('now') → unchanged.
    sql = "UPDATE t SET x=%s WHERE id=%s"
    assert _rewrite_sql(sql) == sql


def test_insert_or_ignore_becomes_on_conflict_do_nothing():
    out = _rewrite_sql("INSERT OR IGNORE INTO posts (slug) VALUES (?)")
    assert out == "INSERT INTO posts (slug) VALUES (%s) ON CONFLICT DO NOTHING"


def test_insert_or_ignore_multiline_and_trailing_ws():
    out = _rewrite_sql(
        "INSERT OR IGNORE INTO hashtag_usage (hashtag, queried_date)\n"
        "               VALUES (?, ?)\n            "
    )
    assert out.rstrip().endswith("ON CONFLICT DO NOTHING")
    assert "OR IGNORE" not in out
    assert "VALUES (%s, %s)" in out


# ── dual-access row (mirrors sqlite3.Row: both row["col"] and row[0]) ──────────
def test_row_supports_named_and_positional_access():
    from utils.db import _Row

    row = _Row(["id", "name"], (5, "moringa"))
    assert row["id"] == 5
    assert row[0] == 5
    assert row["name"] == "moringa"
    assert row[1] == "moringa"


def test_row_is_dict_convertible_and_truthy():
    from utils.db import _Row

    row = _Row(["id", "name"], (5, "moringa"))
    assert dict(row) == {"id": 5, "name": "moringa"}
    assert bool(row) is True  # `row and row[0]` idiom relies on this


# ── dialect-neutral exception aliases (so `except db.IntegrityError` works) ────
def test_exception_aliases_default_to_sqlite():
    import sqlite3
    from utils import db

    # With no DATABASE_URL the live driver is sqlite3; aliases point at it.
    assert db.IntegrityError is sqlite3.IntegrityError
    assert db.OperationalError is sqlite3.OperationalError
