# Audit — current code context (re-audit, 2026-06-20)

This is the ground truth the phase plans build on. Re-run when the code changes.

## What exists and works
- **Python pipeline** (`automation/`): 34 files use `get_db()`; full chain —
  generate prompts/images/video → post organic → create ads (PAUSED) → monitor
  → tune → sync orders → attribution → strategize, plus influencer outreach.
- **Money-safety**: only `apply_approved` raises spend, after an `approved` row +
  cap re-check; enforced by `automation/tests/test_money_safety.py`.
  `config.AUTONOMY_MODE` defaults to **propose** (never auto-applies).
- **Web** (`platform/apps/web`): 6 dashboard screens + APIs, RBAC
  (`requireRole`), HMAC-signed session + login/logout, audit log, `/api/health`.
- **Data model**: `platform/packages/db/schema.prisma` has all 15 tables +
  `Org`/`User`. Prisma migration `0001_init` is committed.
- **Queue seam**: `platform/apps/web/lib/queue.ts` (Redis enqueue) +
  `platform/workers/{run_job,dispatch,reliability}.py` (9 job handlers).
- CI (`.github/workflows/ci.yml`), 21 pytest + 4 worker tests green.

## The one structural problem: split-brain storage
- Pipeline writes **SQLite** (`automation/db/pipeline.db`); web reads
  **Postgres**. `seed_from_sqlite.py` is a one-way bridge → the dashboard shows
  stale/partial reality. **This is the root blocker for go-live and for AaaS.**

## Migration surface (SQLite → Postgres) — measured, not guessed
Good news first:
- **Table names already match** SQLite `schema.sql` ↔ Prisma `@@map` (posts,
  creatives, ad_campaigns, insights_cache, influencers,
  influencer_conversations, orders, attribution, approval_queue, build_tasks,
  audit_log, …). No table renames needed.
- Only **~12** `execute(... ?)` parameterised calls across the codebase.

Real work (mechanical, bounded):
1. **Placeholders**: SQLite `?` → psycopg `%s`. ~12 call sites, or a shim.
2. **SQLite functions in queries**: `datetime('now')` (~7), `strftime` (2),
   `INSERT OR IGNORE` (1–2). Map → `now()`, `to_char(...)`,
   `INSERT ... ON CONFLICT DO NOTHING`. `ON CONFLICT` is already PG-valid.
3. **Types**: SQLite booleans are 0/1 ints; Postgres is real `boolean`
   (`seed_from_sqlite` already lists `BOOL_COLUMNS`). `AUTOINCREMENT` →
   Prisma already emits identity columns. `datetime('now')` text defaults →
   already `DateTime @default(now())` in Prisma.
4. **Driver**: `automation/utils/db.py` uses `sqlite3` (`PRAGMA`, `executescript`,
   `sqlite3.Row`). Swap for `psycopg` with a dict row factory.
5. **Config**: `config.py` has `DB_PATH`, no `DATABASE_URL`, no `load_dotenv`.
   Add dotenv + a `DATABASE_URL` switch (Postgres in prod, SQLite fallback local).

**Recommended approach** (least churn): a thin connection wrapper in
`utils/db.py` that (a) connects via `psycopg` when `DATABASE_URL` is set, else
SQLite, and (b) rewrites `?`→`%s` and `datetime('now')`→`now()` in `execute`.
Keeps the ~34 command files almost untouched; hand-fix only `strftime` /
`INSERT OR IGNORE` (handful). **Prisma becomes the single schema source of
truth**; `automation/db/schema.sql` kept only for local SQLite dev.

## Multi-tenancy gap (for AaaS)
- Only `User` has `orgId`. No business table is org-scoped; no query filters by
  org. Correct for one brand; **the #1 item before a 2nd tenant** (Phase 3).

## Secrets the live agent needs (23)
`ANTHROPIC_API_KEY`, `FAL_KEY`, `BYTEPLUS_ARK_API_KEY`, `CLOUDINARY_CLOUD_NAME`/
`_API_KEY`/`_API_SECRET`, `META_ACCESS_TOKEN`/`_AD_ACCOUNT_ID`/`_APP_ID`/
`_APP_SECRET`/`_IG_ACCOUNT_ID`/`_PAGE_ID`/`_CUSTOMER_AUDIENCE_ID`,
`SHOPIFY_STORE_URL`/`_ACCESS_TOKEN`, `GOOGLE_API_KEY`/`_SHEETS_ID`/
`_SERVICE_ACCOUNT_FILE`, `YOUTUBE_API_KEY`, `SENDGRID_API_KEY`, `FOUNDER_EMAIL`,
+ `SESSION_SECRET`/`ADMIN_PASSWORD` (dashboard). `GOOGLE_SERVICE_ACCOUNT_FILE`
is a file path → on serverless, switch to a base64 env var.

## Scheduling basis (from `crontab.example`)
Stages already mapped to times (generate/post ~9am Mon/Wed/Fri, monitor 6pm,
attribution 7pm, youtube cross-post). These become GitHub Actions cron jobs.
