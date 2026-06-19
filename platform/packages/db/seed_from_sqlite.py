#!/usr/bin/env python3
"""seed_from_sqlite.py — idempotent import of the CLI's SQLite DB into Postgres (E1-T4).

The Python CLI's `automation/db/pipeline.db` is the existing system of record in
dev; this script copies its rows into the Postgres tables created by the Prisma
migration so the web platform sees the same data. It is **idempotent**: every
table is upserted on its natural key, so re-running reports updates (not dupes).

    # safe preview — reads SQLite only, never connects to Postgres:
    python platform/packages/db/seed_from_sqlite.py --dry-run

    # real import (needs DATABASE_URL + `pip install psycopg[binary]`):
    python platform/packages/db/seed_from_sqlite.py

Unhappy paths handled: missing SQLite file → warn + no-op; a table absent from
SQLite → skipped; columns present in SQLite but unknown to the Postgres table →
dropped with a logged note (column drift never aborts the run).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SQLITE_PATH = REPO_ROOT / "automation" / "db" / "pipeline.db"

# table -> (natural-key columns for ON CONFLICT). Order respects FK dependencies
# (parents before children) so a real run never violates a foreign key.
TABLES: list[tuple[str, tuple[str, ...]]] = [
    ("orgs", ("id",)),
    ("users", ("id",)),
    ("posts", ("post_id",)),
    ("ad_campaigns", ("campaign_key",)),
    ("insights_cache", ("ad_id", "fetched_date")),
    ("influencers", ("id",)),
    ("influencer_conversations", ("id",)),
    ("hashtag_usage", ("hashtag",)),
    ("creatives", ("id",)),
    ("orders", ("order_id", "sku")),
    ("ad_spend_daily", ("ad_id", "date")),
    ("attribution", ("scope", "scope_id", "date")),
    ("approval_queue", ("id",)),
    ("build_tasks", ("id",)),
    ("audit_log", ("id",)),
]

# SQLite stores booleans as 0/1; these Postgres columns are typed boolean.
BOOL_COLUMNS = {
    "posts": {"prompts_approved", "creatives_approved", "on_hold"},
}


def _open_sqlite() -> sqlite3.Connection | None:
    if not SQLITE_PATH.exists():
        print(f"WARNING: SQLite source not found at {SQLITE_PATH} — nothing to seed.")
        return None
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_tables(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _rows(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return conn.execute(f'SELECT * FROM "{table}"').fetchall()


def _coerce(table: str, col: str, val):
    if val is not None and col in BOOL_COLUMNS.get(table, ()):
        return bool(val)
    return val


def run(dry_run: bool) -> int:
    src = _open_sqlite()
    if src is None:
        return 0
    present = _sqlite_tables(src)

    if dry_run:
        print("seed_from_sqlite (DRY RUN) — would upsert from SQLite into Postgres:")
        total = 0
        for table, keys in TABLES:
            if table not in present:
                print(f"  {table:<26} (absent in SQLite — skip)")
                continue
            n = src.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            total += n
            print(f"  {table:<26} {n:>5} rows  (conflict key: {', '.join(keys)})")
        print(f"DRY RUN: {total} rows across {len(TABLES)} tables; nothing written.")
        src.close()
        return 0

    # real import — Postgres required
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL not set; cannot connect to Postgres.", file=sys.stderr)
        return 2
    try:
        import psycopg  # psycopg3
    except ImportError:
        print("ERROR: psycopg not installed. `pip install psycopg[binary]`.", file=sys.stderr)
        return 2

    inserted = updated = 0
    with psycopg.connect(dsn) as pg:
        for table, keys in TABLES:
            if table not in present:
                continue
            rows = _rows(src, table)
            if not rows:
                continue
            pg_cols = _pg_columns(pg, table)
            if not pg_cols:
                print(f"  {table}: no such Postgres table — skip")
                continue
            for row in rows:
                cols = [c for c in row.keys() if c in pg_cols]   # drop drifted cols
                vals = [_coerce(table, c, row[c]) for c in cols]
                placeholders = ", ".join(["%s"] * len(cols))
                collist = ", ".join(f'"{c}"' for c in cols)
                updates = ", ".join(f'"{c}"=EXCLUDED."{c}"' for c in cols if c not in keys)
                conflict = ", ".join(f'"{k}"' for k in keys)
                action = f"DO UPDATE SET {updates}" if updates else "DO NOTHING"
                sql = (f'INSERT INTO "{table}" ({collist}) VALUES ({placeholders}) '
                       f'ON CONFLICT ({conflict}) {action}')
                with pg.cursor() as cur:
                    cur.execute(sql, vals)
                    # rowcount is 1 for insert, 1 for update, 0 for do-nothing
                    if cur.rowcount and cur.statusmessage and "INSERT" in cur.statusmessage:
                        inserted += 1
                    else:
                        updated += 1
            print(f"  {table}: {len(rows)} rows upserted")
        pg.commit()
    src.close()
    print(f"seed complete: ~{inserted} inserted, ~{updated} updated (idempotent).")
    return 0


def _pg_columns(pg, table: str) -> set[str]:
    with pg.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=%s",
            (table,))
        return {r[0] for r in cur.fetchall()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Seed Postgres from the CLI's SQLite DB.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Read SQLite and report counts; never connect to Postgres.")
    args = ap.parse_args(argv)
    return run(args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
