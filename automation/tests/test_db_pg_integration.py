"""Opt-in Postgres smoke for the shim. Skipped unless DATABASE_URL points at a
real Postgres (local docker-compose, CI service container, or Neon). Validates
the parts that CANNOT be exercised on SQLite: psycopg row factory (named +
positional), `with db:` transaction commit/rollback, RETURNING, the
`INSERT OR IGNORE`→`ON CONFLICT DO NOTHING` rewrite, and `datetime('now')`.

Run locally:  docker compose -f platform/docker-compose.yml up -d postgres
              DATABASE_URL=postgresql://moregreen:moregreen@localhost:5432/moregreen \
                python -m pytest tests/test_db_pg_integration.py -q
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

if not os.getenv("DATABASE_URL"):
    pytest.skip("DATABASE_URL not set — Postgres smoke skipped", allow_module_level=True)

from utils.db import get_db  # noqa: E402


@pytest.fixture
def pg():
    # Bypass the shim (it no-ops DDL on PG) to set up a scratch table, then
    # hand the shim connection to the tests.
    import psycopg
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url, autocommit=True) as setup:
        setup.execute("DROP TABLE IF EXISTS _shim_smoke")
        setup.execute(
            "CREATE TABLE _shim_smoke (id serial PRIMARY KEY, slug text UNIQUE,"
            " note text, updated_at timestamptz)"
        )
    db = get_db()
    yield db
    db.close()
    with psycopg.connect(url, autocommit=True) as t:
        t.execute("DROP TABLE IF EXISTS _shim_smoke")


def test_returning_and_named_and_positional_rows(pg):
    with pg:
        cur = pg.execute(
            "INSERT INTO _shim_smoke (slug, note, updated_at) "
            "VALUES (?, ?, datetime('now')) RETURNING id",
            ("moringa", "why?"),
        )
        new_id = cur.fetchone()[0]
    row = pg.execute("SELECT id, slug, note FROM _shim_smoke WHERE id=?", (new_id,)).fetchone()
    assert row["slug"] == "moringa" and row[1] == "moringa"   # named + positional
    assert row["note"] == "why?"                              # '?' in literal survived
    assert pg.execute("SELECT updated_at FROM _shim_smoke WHERE id=?", (new_id,)).fetchone()[0]


def test_insert_or_ignore_is_idempotent(pg):
    for _ in range(2):
        with pg:
            pg.execute("INSERT OR IGNORE INTO _shim_smoke (slug) VALUES (?)", ("dup",))
    n = pg.execute("SELECT count(*) FROM _shim_smoke WHERE slug=?", ("dup",)).fetchone()[0]
    assert n == 1


def test_with_block_rolls_back_on_error(pg):
    try:
        with pg:
            pg.execute("INSERT INTO _shim_smoke (slug) VALUES (?)", ("rollme",))
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    n = pg.execute("SELECT count(*) FROM _shim_smoke WHERE slug=?", ("rollme",)).fetchone()[0]
    assert n == 0
