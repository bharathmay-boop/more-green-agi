# More Green — Plans

Detailed, code-grounded sub-plans. The executive summary lives in
[`../ROADMAP.md`](../ROADMAP.md); this directory is the build detail.

Read in order:

| File | What | Needs you? | Effort |
|------|------|-----------|--------|
| [00-audit.md](00-audit.md) | Current-code audit the plans rest on | — | — |
| [01-phase0-unify-postgres.md](01-phase0-unify-postgres.md) | One DB (Postgres), drop Redis from critical path | No | ~1 session |
| [02-phase1-go-live.md](02-phase1-go-live.md) | Deploy: Vercel + Neon + GitHub Actions cron → **Goal 1 live** | Yes (~30 min) | ~1 session |
| [03-phase2-portfolio.md](03-phase2-portfolio.md) | Case study + safe demo → **Goal 2** | A little | ~½ session |
| [04-phase3-aaas-foundation.md](04-phase3-aaas-foundation.md) | Multi-tenancy + real auth + secret vault | No | several |
| [05-phase4-monetization.md](05-phase4-monetization.md) | OAuth onboarding + Stripe → **Goal 3 sellable** | Yes (app review) | several |

## Sequencing logic
- **0 before everything** — single shared DB is the hard prerequisite for both
  go-live and multi-tenancy.
- **1 next** — prove the agent on the real brand before adding SaaS complexity.
- **2 right after 1** — packaging is cheap once it's live; lock in the portfolio.
- **3 then 4** — never add billing/onboarding before tenant isolation exists.

## Hosting decision
**Path A** — Vercel + Neon + GitHub Actions cron (~$0/mo, no Docker/Redis/
always-on worker). Rationale and the Path-B alternative are in `../ROADMAP.md`.

## Critical-path call-outs (from the audit)
- Phase 0's real work is bounded: table names already match across SQLite/Prisma;
  the churn is `?`→`%s`, a few SQLite-only SQL functions, and the driver swap —
  handled by a thin shim, not a rewrite.
- Phase 4's make-or-break is **per-tenant Meta/Shopify OAuth onboarding**, plus
  the **weeks-long Meta/Shopify app review** — start that review early.
