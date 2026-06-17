# 09 — Verification, Testing, CI

Everything below runs **without spending money** and degrades gracefully in this sandbox (no Postgres/Redis/Meta) via dry-run + mock adapters.

## Sandbox-safe checks (I run these before PR)
1. **Schema parity:** `python -c "import sys; sys.path.insert(0,'automation'); from utils.db import get_db; get_db()"` creates all new SQLite tables; assert tables exist.
2. **Build Engine:** `python build/orchestrate.py --dry-run` lists ready tasks in dependency order, dispatches nothing. `python build/orchestrate.py --dispatch=mock --parallel 1` runs the loop end-to-end on a no-op task, commits, regenerates `BUILD_PLAN.md`. `bash build/resume.sh --once --dry-run` exercises lock + backoff path.
3. **Profit loop (dry):** `python automation/main.py --dry-run sync-orders` prints counts, writes nothing; with a seeded fixture DB, `compute-attribution` produces rows; unit tests cover ÷0, refunds, multi-SKU split, IST bucketing.
4. **Approval safety (the critical tests):**
   - grep/test assert **no** Meta budget/activate call exists outside `apply_approved.py`.
   - `tune_ads` on a high-ROAS fixture writes a `scale_budget` proposal and makes **no** Meta call.
   - `tune_ads` on a low-CTR fixture **pauses immediately** (allowed) — asserted.
   - `apply_approved` with a cap-breaching row → `failed`, no Meta call.
   - illegal status transition raises.
5. **Prisma:** `cd platform/packages/db && npx prisma validate` (no DB needed); `prisma migrate diff` if Postgres present.
6. **Web build:** `cd platform/apps/web && npm install && npm run build` passes; typecheck clean. `npm run dev` against docker Postgres (or mock adapter) renders the 5 screens.
7. **seed_from_sqlite idempotency:** run twice → second run reports 0 inserts / N updates, no dupes.

## Test suites (added; run in CI)
- `automation/tests/` (pytest): `test_attribution.py`, `test_approval_queue.py`, `test_tune_ads_proposals.py`, `test_sync_orders.py`, `test_orchestrator.py` (mock dispatch). Extend existing `test_seed_calendar.py` patterns.
- `platform/apps/web` (vitest + RTL): CRUD route handlers, approval state machine, ROAS aggregation.
- **CI** (E9): GitHub Actions — pytest + vitest + `prisma validate` + `npm run build` on PR.

## Manual end-to-end (user's real environment, post-merge)
With real creds: `sync-orders` → `monitor-ads` → `compute-attribution` → open ROAS dashboard; create a campaign (PAUSED) → approve `activate_ad` in web → `apply-approved` flips it live; install cron (`crontab -e` per `build/README.md`) and confirm `resume.sh` continues the backlog after a forced interrupt.

## Definition of done for THIS run
- E0 + E1 complete; E2-T1..T4, E3-T1..T4, E4 functional in dry-run/mock.
- All sandbox-safe checks (1–7) green.
- Money-safety tests (#4) green.
- Build Engine armed (cron documented); `BUILD_PLAN.md` reflects remaining backlog.
- PR opened with summary + how-to-run + safety notes.
