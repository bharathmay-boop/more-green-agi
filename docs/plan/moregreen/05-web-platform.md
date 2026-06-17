# 05 — Web Control Plane (Next.js)

`platform/apps/web` — Next.js 15 App Router + TypeScript, talking to Postgres via Prisma (`platform/packages/db`). Replaces the Streamlit dashboard as the SaaS control plane; the existing `_dashboard_app.py` approval logic is the behavioral spec we port.

## Layout
```
platform/
  docker-compose.yml          # postgres:16, redis:7
  packages/db/                # schema.prisma, client, migrations, seed_from_sqlite.py
  packages/core/              # shared TS types/enums (mirror Prisma)
  apps/web/
    app/
      (dash)/calendar/        # content calendar + post CRUD
      (dash)/creatives/       # creative review + variant select
      (dash)/approvals/       # approval queue
      (dash)/roas/            # ROAS dashboards
      (dash)/build/           # Build Engine status (build_task)
      (dash)/audit/           # audit_log
      api/                    # route handlers (REST) — see below
    lib/db.ts, lib/auth.ts, lib/queue.ts
  workers/                    # Python entrypoints wrapping automation/commands
```

## Resources & CRUD (REST route handlers + Server Actions)
| Route | GET | POST | PATCH | DELETE |
|---|---|---|---|---|
| `/api/posts` | list/filter by week/status | create post | update fields/approval flags/status | archive (soft) / hard-delete (owner) |
| `/api/posts/:id/generate` | — | enqueue prompts/creatives job | — | — |
| `/api/creatives` | list by post | enqueue generation | select/reject variant | delete failed variant (+Cloudinary) |
| `/api/orders` | list/aggregate | trigger sync-orders job | — | — (financial) |
| `/api/attribution` | ROAS rollups by sku/campaign/range | recompute job | — | — |
| `/api/approvals` | list pending/decided | (producers only) | approve/reject | — (TTL expire job) |
| `/api/approvals/:id/apply` | — | enqueue apply-approved | — | — |
| `/api/build-tasks` | list/status | — | reset blocked→todo | — |
| `/api/audit` | list/filter | — | — | — |

- Jobs are enqueued to Redis (`lib/queue.ts`); Python workers consume and call existing `automation/commands/*`. Web shows job status (queued/running/done/failed) by polling.
- Server Actions used for in-page mutations (approve, select variant, edit caption) with optimistic UI + rollback on error.

## Screens (happy + error states)
- **Calendar** — week grid of posts with status badges; create/edit/hold/archive; click → detail (edit prompts/captions, trigger generate). Empty state, loading skeletons, error toasts.
- **Creative Review** — variant carousel, select winner (sets `creative.status=selected`, `post.creatives_approved`), regenerate, reject. Mirrors Streamlit `screen_creative_approval`.
- **Approvals** — pending proposals grouped by type; current→proposed + projected ROAS; one-tap Approve/Reject; shows applied/failed history. Cap-breach badge.
- **ROAS** — blended vs paid ROAS by SKU/campaign, spend, revenue, trend; below-target highlighting; date-range filter.
- **Build** — epic progress bars, ready/blocked tasks, last error, "reset task" action (mirrors `BUILD_PLAN.md`).
- **Audit** — append-only log with filters.

## Auth (E9; stubbed now)
- `lib/auth.ts` with a single-org dev bypass now; NextAuth + org/role (owner|approver|viewer) later. Approve/apply gated to `approver|owner`. All mutations write `audit_log`.

## Build/runtime
- `npm install && npm run build` must pass (CI gate). `npm run dev` serves against docker Postgres or a seeded SQLite-backed mock adapter when no DB (sandbox fallback).
- Unhappy: DB down → friendly error boundary + retry; queue down → mutations disabled with banner; stale data → SWR revalidation.
