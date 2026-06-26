# 08 — Epic → Story → Task Backlog (seed for `build/backlog.yaml`)

Tasks are file-disjoint within a parallel batch; `depends_on` serializes overlaps. `[R]` = done in THIS run by me; unmarked = Build Engine continues. Each task in `backlog.yaml` carries `acceptance` + `verify`.

## E0 — Build Engine & cron  `[R]`
- E0-T1 `build/backlog.yaml` seeded with this breakdown.
- E0-T2 `build/orchestrate.py` (ready-set, dispatch, verify, commit, regen, lock, `--parallel`, `--dry-run`, `--dispatch=mock`).
- E0-T3 `build/resume.sh` (flock, stale-lock reclaim, backoff, WIP safeguard).
- E0-T4 `BUILD_PLAN.md` generator + `state.json`.
- E0-T5 cron line in `automation/crontab.example` + `build/README.md`.
- Deps: T2→T1; T3,T4→T2; T5→T3.

## E1 — Platform foundation  `[R]`
- E1-T1 `platform/docker-compose.yml` (postgres+redis).
- E1-T2 `platform/packages/db/schema.prisma` (port existing + new tables, doc 01).
- E1-T3 prisma migrations + `lib/db.ts` client.
- E1-T4 `seed_from_sqlite.py` (idempotent import).
- E1-T5 `automation/db/schema.sql` new tables (CLI parity).
- E1-T6 Next.js app skeleton + layout + `lib/queue.ts`.
- E1-T7 Calendar screen + `/api/posts` CRUD.
- E1-T8 Creative Review screen + `/api/creatives` CRUD.
- E1-T9 worker bridge `platform/workers/*` wrapping `automation/commands/*`.
- Deps: T3→T2; T4→T3; T7,T8→T6+T3; T9→T1.

## E2 — Profit loop  `[R-start]`
- E2-T1 `sync_orders.py` + `sync-orders` CLI + `order` table.
- E2-T2 extend `monitor_ads.py` → `ad_spend_daily` per-day upsert.
- E2-T3 `attribution.py` + `compute-attribution` (ROAS rollups, ÷0/refund/split safe).
- E2-T4 ROAS dashboard screen + `/api/attribution`.
- E2-T5 extend `export_report.py` blended-ROAS section.
- Deps: T2→E1-T5; T3→T1,T2; T4→T3+E1-T6; T5→T3.

## E3 — Approval-gated spend  `[R-start]`
- E3-T1 `approval_queue` table + producer helper.
- E3-T2 refactor `tune_ads.py` (SCALE/activate→proposal; PAUSE immediate).
- E3-T3 `apply_approved.py` + `apply-approved` CLI (cap re-check, idempotent).
- E3-T4 Approvals screen + `/api/approvals` approve/reject/apply.
- E3-T5 caps/config in `config.py`; email deep-link approve.
- Deps: T2,T3→T1; T4→T1+E1-T6; T3→T5.

## E4 — Strategist (first cut)  `[R]`
- E4-T1 `strategize.py` (Claude allocation → draft posts + proposals).
- E4-T2 `strategize` CLI + Build screen surfacing.
- Deps: T1→E2-T3,E3-T1.

## E5 — Creative Studio
- multi-variant gen; per-pillar caption/hashtag; banned-phrase lint+regenerate; CTR-fed variant scoring; Creative CRUD polish. (5–7 tasks)

## E6 — Calendar Autopilot
- auto-seed posts from cultural calendar + perf gaps + sku_split; dedupe; weekly approval. (4 tasks)

## E7 — Storefront / Product-Page Loop
- read products + landing perf; copy/price-test proposals; write-gated `Product.save`; margin guardrails. (5 tasks)

## E8 — Channels
- influencer CRM + conversations in web; YouTube Shorts auto cross-post; email/WhatsApp lifecycle. (6 tasks)

## E9 — SaaS hardening
- NextAuth + org/RBAC; secrets vault; queue retries/DLQ; observability; pytest + vitest + GitHub Actions CI; load/retention jobs. (8 tasks)

## Implementation order for THIS run (me)
E0 (all) → E1 (all) → E1-T5 schema → E2-T1..T4 → E3-T1..T4 → E4-T1..T2 → arm cron → verify (doc 09) → commit → **open PR**. Remaining E2-T5, E5–E9 left armed in backlog for autonomous continuation.
