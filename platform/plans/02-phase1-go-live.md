# Phase 1 — Go live (Vercel + Neon + GitHub Actions)

**Goal:** More Green's marketing agent running 24/7 in the cloud, dashboard on a
real URL, **supervised** (you approve every spend before it applies). → Goal 1.

**Precondition:** Phase 0 done (single Postgres DB, no Redis). Per Phase 0 D1
the job queue is deferred to P3/4 — there is no `process-jobs`; the scheduled
`apply-approved` run is the apply path. The cron workflow already exists at
`.github/workflows/pipeline.yml` (dormant until `vars.PIPELINE_ENABLED=true`).

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
- ~~Confirm `apps/web` build runs `prisma migrate deploy && prisma generate &&
  next build`~~ **DONE** — `apps/web/vercel.json` sets that `buildCommand` (so the
  schema applies on first deploy). CI's `npm run build` stays migration-free, so
  it never needs a live DB. Caveat: every Vercel build (incl. preview) needs a
  reachable `DATABASE_URL`, or `migrate deploy` fails the build — set it for all
  environments, or scope previews to a Neon branch.
- **Acceptance:** Vercel build green; `https://<app>.vercel.app/api/health`
  returns `{ok:true, db:true}` (redis check removed/ignored).

## Task 1.3 — Seed owner user + initial data
- ~~Create the owner row in Neon~~ **DONE** — `python main.py seed-owner
  --email <you> [--org-name "More Green"]` (idempotent; runs against Neon when
  `DATABASE_URL` is set). Login still needs `ADMIN_PASSWORD` set on the web tier.
- One-time backfill of existing SQLite data → Neon via `seed_from_sqlite.py`
  pointed at `DATABASE_URL` (it already upserts). After this, SQLite is retired.
- **Acceptance:** login via `/api/auth/login` succeeds; dashboard shows real
  posts/orders.

## Task 1.4 — Pipeline on GitHub Actions cron
- Add `.github/workflows/pipeline.yml` with jobs mirroring `crontab.example`:
  - `generate` + `post_organic` (Mon/Wed/Fri ~9am IST → cron in UTC),
  - `monitor_ads` (daily 6pm IST), `attribution` (7pm IST),
  - `sync_orders` (daily),
  - `apply-approved` (every ~10 min — applies approved proposals after a cap
    re-check; replaces the deferred job queue).
  - (TTL expiry of stale pending proposals: `utils/approvals.expire_stale`
    exists but has no CLI command yet — harmless to defer; pending rows never
    auto-apply. Add an `expire-approvals` command if the queue grows noisy.)
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
