# More Green Platform — B2B SaaS Unicorn Audit

_Date: 2026-06-19 · Scope: `platform/` (Next.js web tier, Prisma/Postgres, Python workers) + `automation/` CLI._

Lens: "what would a Series-A → unicorn-track B2B SaaS need here." Each gap is
rated by **value now** (this is a single-brand internal tool today) vs.
**effort**. I built the high-value/low-effort ones this pass; the rest are
planned with an honest "add when" trigger so we don't gold-plate a one-tenant app.

---

## What's already solid

- **Money-safety invariant is real and tested.** Only `apply_approved` raises Meta spend, only after an `approved` row + cap re-check (`automation/tests/test_money_safety.py`). The web `apply` route only enqueues — never touches Meta. This is the hardest thing to get right and it's right.
- **RBAC seam exists** (`lib/auth.ts`, `requireRole`) gating approve/apply to approver|owner, secure-by-default viewer.
- **Worker reliability**: retries + DLQ + metrics (`workers/reliability.py`).
- **CI + pytest** (21 tests) + a deterministic Prisma migration.
- **Screens degrade gracefully** via `safeQuery` — DB down never 500s the dashboard.

---

## Gaps, ranked

### 1. Audit trail not written — BUILT THIS PASS ✅
`audit_log` table + `/audit` screen existed only as a stub; **nothing wrote to it.**
For a money-moving product the "who approved this spend, when, before→after"
trail is table stakes (SOC2, dispute resolution, debugging a bad apply).
→ Wired `writeAudit()` into approve/reject/apply and influencer status changes;
made `/audit` a real screen. Value: high. Effort: low.

### 2. Health/readiness endpoint — BUILT THIS PASS ✅
No way to know if the web tier can reach Postgres/Redis without loading a page.
→ Added `GET /api/health` (checks DB + Redis, returns 200/503). Value: high
(uptime monitoring, load-balancer probes). Effort: low.

### 3. Input validation at the API trust boundary — BUILT THIS PASS ✅ (partial)
Routes did `body.action as Action` / `Number(id)` with loose parsing. A `NaN`
id or unexpected field reached Prisma. → Hardened the money path (approvals)
and id parsing. Value: high (trust boundary). Effort: low.
Remaining: a shared zod schema per route — add when routes are public-facing.

### 4. Multi-tenancy is nominal — PLANNED, deliberately deferred
Only `User` has `orgId`. No business table (Post, AdCampaign, Order,
ApprovalQueue…) is tenant-scoped and no query filters by org. **For one brand
this is correct (YAGNI).** The day a second tenant exists this is the #1
security item: every business model needs `orgId` + every query a `where:{orgId}`
+ a Prisma middleware to enforce it so nobody can forget.
→ Add when: a second org is onboarded. Tracked as a backlog epic, not built.

### 5. Real auth provider — PLANNED
`getCurrentUser` reads an `mg_session` cookie (email) with a `DEV_ROLE` escape
hatch. No login, no session signing, no expiry. Fine for a single internal
operator behind a VPN; not fine for external users.
→ Add when: anyone outside the founding team logs in. Swap the cookie lookup
for Auth.js — route guards stay unchanged (the seam was built for this).

### 6. Billing / metering — PLANNED, speculative
No plans, usage metering, or Stripe. `Org.plan` is a string stub.
→ Add when: charging a customer. Pure YAGNI until then.

### 7. Observability beyond health — PLANNED
Workers emit metrics to Redis; the web tier has no error tracking (Sentry) or
structured request logs. → Add when: first production incident you can't
explain from logs. Low effort to add Sentry; skipped to avoid a dep nobody's
paging on yet.

### 8. Secrets — note
`.env` is gitignored and `git rm --cached`'d (good). For deploy, move to the
host's secret store (Vercel/Fly env, not a file). No code change needed now.

---

## Build summary (this pass)

| # | Item | Status |
|---|------|--------|
| 1 | Audit logging on money + status actions | ✅ built |
| 2 | `/api/health` (DB + Redis) | ✅ built |
| 3 | Input validation on approval/id paths | ✅ built |
| 4 | `/audit` screen | ✅ built |
| 5–8 | tenancy, auth, billing, Sentry | planned w/ triggers |

The deferred items are deferred because the app is single-tenant today, not
because they're unimportant — each has a named "add when" trigger above.
