# More Green — Go-Live & Product Roadmap

Three goals, one codebase:
1. **Run More Green's marketing on autopilot** (real Marketing Agent).
2. **Portfolio piece** (a live, showable system).
3. **Bootstrapped Agent-as-a-Service (AaaS)** with monetization.

> **This is the executive summary.** The extensive, code-grounded build detail
> is split into per-phase sub-plans in [`plans/`](plans/README.md), backed by a
> fresh code audit in [`plans/00-audit.md`](plans/00-audit.md).

---

## Hosting decision (goals incorporated): **Path A — all-managed, ~$0/mo**

Vercel (web) + Neon (Postgres) + GitHub Actions cron (pipeline). No Docker, no
Redis, no always-on worker, nothing on your laptop, reachable from your phone.

Why this serves all three goals, not just goal 1:
- **Goal 1:** $0 and always-on — the agent runs whether your laptop is on or not.
- **Goal 2:** gives you a live URL + a clean, genuinely impressive architecture
  (agent loop, money-safety gate, RBAC, audit trail) to demo.
- **Goal 3:** the one big refactor Path A requires — **unifying on Postgres** —
  is a *hard prerequisite for multi-tenant SaaS anyway*. The Redis+worker infra
  we skip now is cheap to re-add the day a paying tenant needs scale. That is
  exactly bootstrapping: don't pay for SaaS infrastructure before a customer
  pays you.

Path B (Upstash + Railway worker, ~$10/mo) is only worth it if you want it live
in the next hour with zero refactor. It does not get you closer to goal 3.

---

## Where each goal stands today

The build is real, not a skeleton: 41/41 backlog tasks, full Python pipeline
(generate → post → ads → monitor → tune → attribution → strategist +
influencer outreach), money-safety enforced & tested, 6 dashboard screens, RBAC,
audit log, health check, signed-cookie login, CI.

| Goal | % there | The long pole |
|------|---------|---------------|
| 1. Live agent | ~80% | deploy + unify SQLite→Postgres + wire secrets + supervised burn-in |
| 2. Portfolio | ~70% | mostly packaging once #1 is live (README/case study, read-only demo) |
| 3. AaaS | ~15% | per-tenant OAuth onboarding + billing + multi-tenancy enforcement |

---

## Phased plan

### Phase 0 — Single-DB foundation  *(I can build now, no accounts needed)*
The blocker for everything: the pipeline writes SQLite, the web reads Postgres.
- Migrate `automation/utils/db.py` (and SQL dialect quirks) to Postgres via
  `DATABASE_URL`; keep SQLite as a local-dev fallback.
- Replace the web's Redis `enqueueJob` with a Postgres `jobs` table + a
  `python main.py process-jobs` drainer (money-safety unchanged).
- Add `.github/workflows/pipeline.yml`: scheduled stages + a short-interval
  job that applies approved proposals and drains `jobs`.
→ Output: deploy-ready on one database, no Redis.

### Phase 1 — Go live  *(needs you: ~30 min of signups + secrets)*
- You create **Neon** (free) and **Vercel** (free), connect the GitHub repo.
- You provide the 23 API secrets (list below); I set them as Vercel + GitHub
  Actions secrets and do the first deploy + migration.
- Run in **supervised mode** first: agent proposes, you approve everything in
  the dashboard before any spend. → **Goal 1 live.**

### Phase 2 — Portfolio packaging  *(I build, ~half a session)*
- README/case study (problem → architecture → money-safety → results).
- Read-only **demo account** (viewer role) so anyone can click around safely.
- Optional short walkthrough video. → **Goal 2 done.**

### Phase 3 — AaaS foundation  *(I build)*
- **Multi-tenancy:** add `orgId` to every business model + a Prisma middleware
  that auto-scopes every query (so no route can leak across tenants).
- **Real auth:** Auth.js login page replacing the shared password.
- **Per-tenant secret vault:** customers' Meta/Shopify keys stored encrypted
  per org, not in global env.

### Phase 4 — Monetization  *(I build; the make-or-break is onboarding)*
- **Self-serve onboarding:** each customer connects *their own* Meta ad account
  + Shopify store via OAuth. This is the hardest, highest-value piece — without
  it AaaS can't exist.
- **Stripe** plans + usage metering + per-plan spend/generation caps.
  → **Goal 3 sellable.**

---

## What I need from you to start Phase 1

Accounts (free): **Neon**, **Vercel** (sign in with GitHub).

Secrets to provide (same ones the agent uses today):
`ANTHROPIC_API_KEY`, `FAL_KEY`, `BYTEPLUS_ARK_API_KEY`,
`CLOUDINARY_CLOUD_NAME` / `_API_KEY` / `_API_SECRET`,
`META_ACCESS_TOKEN` / `_AD_ACCOUNT_ID` / `_APP_ID` / `_APP_SECRET` /
`_IG_ACCOUNT_ID` / `_PAGE_ID` / `_CUSTOMER_AUDIENCE_ID`,
`SHOPIFY_STORE_URL` / `SHOPIFY_ACCESS_TOKEN`,
`GOOGLE_API_KEY` / `GOOGLE_SHEETS_ID` / `GOOGLE_SERVICE_ACCOUNT_FILE`,
`YOUTUBE_API_KEY`, `SENDGRID_API_KEY`, `FOUNDER_EMAIL`,
plus `SESSION_SECRET` + `ADMIN_PASSWORD` for the dashboard.
