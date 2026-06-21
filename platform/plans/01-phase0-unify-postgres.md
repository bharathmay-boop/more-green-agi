# Phase 0 — Single-DB foundation (unify pipeline on Postgres)

**Goal:** one database (Postgres) for both the pipeline and the web, so the
dashboard reflects reality and the system is deploy-ready. Remove Redis from the
critical path. **No external accounts needed — fully buildable now.**

**Why first:** every later phase (live agent, AaaS multi-tenancy) requires a
single shared, network-reachable store. SQLite can't be either.

**Effort:** ~1 focused session. **Reversible:** SQLite fallback kept; feature-
flagged by `DATABASE_URL`.

---

## REVISED scope (2026-06-21, post-grill) — read this first

Grilled against the real code. Decisions that override the tasks below:

- **D1 — Defer the queue (Task 0.4).** The scheduled pipeline calls
  `python main.py <stage>` directly (see `crontab.example`); the Redis queue is
  used by only **two on-demand dashboard buttons** (approvals→`apply_approved`,
  creatives→`generate`) + `/api/health`. In Path A there's no always-on worker.
  So Phase 0 **deletes** `lib/queue.ts` + ioredis + `workers/*`, and rewires:
  approve→apply via the existing `approval_queue` row drained by a `*/10`
  GitHub Action running `apply-approved`; regenerate-creative deferred. A real
  job queue returns in **Phase 3/4** when multi-tenant async dispatch needs it.
- **D2 — Shim, with a cached rewrite.** Thin wrapper in `utils/db.py`;
  `?`→`%s` and `datetime('now')`→`now()` rewritten once per SQL string via
  `lru_cache`. Regex skips `?` inside quoted literals (unit-tested).
- **D3 — `with db:` = transaction CM.** Wrapper `__enter__/__exit__` commits on
  success / rolls back on exception. **Never** psycopg3 native `with conn`
  (closes the connection). PG conn `autocommit=False`. ~20 `with db:` untouched.
- **D4 — `lastrowid` → `RETURNING id`.** Only leak is `approvals.py:99`
  (money path). `RETURNING id` is valid on SQLite 3.35+ *and* PG. One explicit
  edit; `test_money_safety.py` is the gate.
- **D5 — Prisma owns the schema on PG.** On Postgres `get_db()` skips
  `_ensure_schema`; shim no-ops `CREATE TABLE/INDEX`/`PRAGMA`. All inline-created
  tables already exist in Prisma (verified). Add missing `ad_campaigns.post_id`
  + migration.
- **D6 — Exception leaks.** `utils/db.py` exports `IntegrityError` /
  `OperationalError` bound to the live driver; the 2 `except sqlite3.X` sites
  (`approvals.py:104`, `export_report.py:47`) switch to `db.X`. `sqlite3.Row`/
  `Connection` type *hints* left as-is (runtime-harmless).
- **D7 — Drop the `strftime` fix** from Task 0.2: `approvals.py:43` &
  `update_tracker.py:214` are Python `datetime.strftime`, not SQL. No-op.
- **D8 — Testing.** Unit/CI through the shim on **SQLite** (placeholder edge
  cases + money-safety); one opt-in integration smoke vs the `docker-compose`
  Postgres, skipped when `DATABASE_URL` unset.

Deferred out of Phase 0: queue (D1)→P3/4, `orgId` scoping→P3,
`GOOGLE_SERVICE_ACCOUNT_B64`→P1 (go-live secrets).

---

## Task 0.1 — DB driver switch in `automation/utils/db.py`
- Add `psycopg[binary]` to `automation/requirements.txt`.
- In `get_db()`: if `os.getenv("DATABASE_URL")` → connect via `psycopg`
  (autocommit off, dict row factory `psycopg.rows.dict_row`); else current
  SQLite path (local dev).
- Wrap the connection so `.execute(sql, params)` rewrites:
  - `?` → `%s` (regex on the SQL string, skipping `?` inside quotes),
  - `datetime('now')` → `now()`.
  Expose `.execute`, `.executemany`, `.commit`, `.close`, and a context-manager
  `with db:` that maps to a transaction (psycopg `with conn.transaction()`).
- Keep `row["col"]` access working (dict_row already gives that; SQLite uses
  `sqlite3.Row` — both support mapping access, so command code is unchanged).
- **Acceptance:** `DATABASE_URL=... python -c "from utils.db import get_db; get_db().execute('SELECT 1')"` works against Neon/local PG.

## Task 0.2 — Hand-fix the non-translatable SQL (handful)
- `strftime(...)` → `to_char(...)` in `utils/approvals.py:43`,
  `commands/update_tracker.py:214`.
- `INSERT OR IGNORE` → `INSERT ... ON CONFLICT DO NOTHING` in
  `commands/strategize.py` (and any others grep finds).
- Audit booleans written as `0/1` against `boolean` columns (posts flags) — psycopg
  accepts Python `bool`; ensure code passes `True/False` or cast in SQL.
- **Acceptance:** `grep -rnE "strftime|INSERT OR (IGNORE|REPLACE)|julianday|datetime\('now'" automation/` returns nothing outside the shim.

## Task 0.3 — Prisma as the single schema source of truth
- Treat `platform/packages/db/schema.prisma` + its migrations as canonical.
- Demote `automation/db/schema.sql` to "local SQLite dev only" (header comment);
  stop using it to create prod tables.
- Verify every column the pipeline writes exists in Prisma with the same
  snake_case name (`@map`). Add any missing columns to Prisma + a new migration
  (e.g. confirm `ad_campaigns.post_id` added in E5 is in Prisma — **it is not yet**;
  add it).
- **Acceptance:** `prisma migrate diff --from-schema-datamodel --to-database` is
  empty after applying; a pipeline dry-run writes rows the dashboard reads.

## Task 0.4 — Replace Redis queue with a Postgres `jobs` table
- Add `Job` model to Prisma: `id`, `type`, `payloadJson`, `status`
  (queued|running|done|failed), `attempts`, `error`, `createdAt`, `startedAt`,
  `finishedAt`, index on `(status, createdAt)`. Migration.
- **Web side** (`lib/queue.ts`): keep the `enqueueJob` signature; change the body
  to `prisma.job.create(...)` instead of Redis LPUSH. `getJob`/`isQueueHealthy`
  read the table / `SELECT 1`. Delete the ioredis dependency from the web build
  (drop from `serverExternalPackages`).
- **Worker side**: new `automation/commands/process_jobs.py` — `SELECT ... FOR
  UPDATE SKIP LOCKED LIMIT n WHERE status='queued'`, mark running, call the
  existing `dispatch()` logic (lift the handler map from
  `platform/workers/dispatch.py` into the automation package so it runs in the
  same process as the cron), mark done/failed with retry count. Reuse
  `workers/reliability.py` retry/backoff semantics.
- Register `process-jobs` CLI command in `main.py` (mirror `score-creatives`).
- **Acceptance:** enqueue from a unit test → `python main.py process-jobs
  --once` runs the handler and flips status to `done`; failure increments
  `attempts` and re-queues then dead-letters per policy.

## Task 0.5 — Config: dotenv + DATABASE_URL
- `automation/config.py`: `from dotenv import load_dotenv; load_dotenv()` at top;
  read `DATABASE_URL`. Add `python-dotenv` to requirements.
- `GOOGLE_SERVICE_ACCOUNT_FILE`: also accept `GOOGLE_SERVICE_ACCOUNT_B64`
  (base64 of the JSON) for serverless; write to a temp file at startup if set.
- **Acceptance:** with a `.env` present, `python main.py --help` loads; with
  `DATABASE_URL` unset, SQLite still works.

## Task 0.6 — Tests
- Extend `automation/tests/` with a `process_jobs` test (enqueue→drain→done,
  and failure→retry→DLQ) using a SQLite test DB through the shim.
- Keep `test_money_safety.py` green (the apply path is unchanged).
- **Acceptance:** `pytest automation/tests -q` all green; `npm run build` green
  after the web queue swap.

---

## Risks & mitigations
- **`?`-inside-string false positives** in the placeholder rewrite → restrict
  regex to `?` not within quotes; add a unit test with a `?`-containing literal.
- **Transaction semantics** differ (SQLite implicit vs psycopg explicit) → the
  `with db:` context manager normalises this; review the few multi-statement
  `with db:` blocks.
- **Column drift** Prisma vs pipeline → Task 0.3 diff check is the gate.
- **Money-safety regression** → `test_money_safety.py` must stay green; do not
  touch `apply_approved` logic, only its DB driver.

## Definition of done
Pipeline + web both run against one Postgres URL; Redis removed from web build;
`process-jobs` drains the queue; all tests + builds green; committed.
