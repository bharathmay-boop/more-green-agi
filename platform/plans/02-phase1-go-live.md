# Phase 1 — Go live (Vercel + Neon + GitHub Actions)

**Goal:** More Green's marketing agent running 24/7 in the cloud, dashboard on a
real URL, **supervised** (you approve every spend before it applies). → Goal 1.

**Precondition:** Phase 0 done (single Postgres DB, `process-jobs`, no Redis).

**Needs you:** ~30 min — create two free accounts + paste secrets. Everything
else is mine.

**Effort (mine):** ~1 session of config + first deploy + smoke test.

---

## Task 1.1 — Provision managed infra (you, guided)
- **Neon** (neon.tech): create project → copy the pooled `DATABASE_URL`.
- **Vercel** (vercel.com, sign in with GitHub): import
  `bharathmay-boop/more-green-agi`, set **root directory** to
  `platform/apps/web`.
- **Acceptance:** Neon URL reachable; Vercel project created (build will fail
  until 1.2 — expected).

## Task 1.2 — Wire web env on Vercel
- Set Vercel env vars: `DATABASE_URL` (Neon), `SESSION_SECRET`, `ADMIN_PASSWORD`.
  (No `REDIS_URL` — removed in Phase 0.)
- Confirm `apps/web` build script runs `prisma migrate deploy && prisma generate
  && next build` (add `migrate deploy` so the schema applies on first deploy).
- **Acceptance:** Vercel build green; `https://<app>.vercel.app/api/health`
  returns `{ok:true, db:true}` (redis check removed/ignored).

## Task 1.3 — Seed owner user + initial data
- Create the owner row in Neon (one SQL insert, or a `main.py seed-owner`
  helper) so login works.
- One-time backfill of existing SQLite data → Neon via `seed_from_sqlite.py`
  pointed at `DATABASE_URL` (it already upserts). After this, SQLite is retired.
- **Acceptance:** login via `/api/auth/login` succeeds; dashboard shows real
  posts/orders.

## Task 1.4 — Pipeline on GitHub Actions cron
- Add `.github/workflows/pipeline.yml` with jobs mirroring `crontab.example`:
  - `generate` + `post_organic` (Mon/Wed/Fri ~9am IST → cron in UTC),
  - `monitor_ads` (daily 6pm IST), `attribution` (7pm IST),
  - `sync_orders` (a few times daily),
  - `process_jobs` (every ~5 min — drains web-enqueued jobs incl.
    `apply_approved`),
  - `expire_approvals` (hourly — TTL per `APPROVAL_TTL_HOURS`).
- All jobs: `pip install -r automation/requirements.txt`, export secrets from
  **GitHub Actions secrets**, `cd automation && python main.py <cmd>`.
- Keep `AUTONOMY_MODE=propose` so nothing applies without an approved row.
- **Acceptance:** a manual `workflow_dispatch` run of `monitor_ads` completes
  green and writes insights rows visible in the dashboard.

## Task 1.5 — Secrets into GitHub Actions
- Add all 23 secrets (see `00-audit.md`) as repo secrets.
  `GOOGLE_SERVICE_ACCOUNT_B64` instead of a file path.
- **Acceptance:** no job fails with a missing-key error.

## Task 1.6 — Supervised burn-in
- Run for a set period with you approving each proposal in `/approvals` before
  `process_jobs` applies it. Watch `/audit` + `/roas`.
- Only after confidence: optionally raise autonomy (still cap-gated).
- **Acceptance:** at least one full loop — generate → approve → apply (within
  caps) → monitor → attribution — observed end to end.

---

## Risks & mitigations
- **GH Actions cron drift/delay** (can lag minutes under load) → fine for this
  workload; `process_jobs` every 5 min bounds apply latency.
- **Secret sprawl / leakage** → GitHub + Vercel secret stores only; never in
  repo; `.env*` already gitignored.
- **First-deploy migration** → `migrate deploy` is idempotent; Neon branch can
  be reset if needed.
- **Cost creep** → Neon + Vercel + Actions all free at this volume; set a Meta
  spend cap (`MAX_DAILY_SPEND_INR=3000`) as the hard money backstop.

## Definition of done
Public dashboard URL, agent running on schedule against Neon, supervised loop
demonstrated, spend gated. **Goal 1 = live.**
