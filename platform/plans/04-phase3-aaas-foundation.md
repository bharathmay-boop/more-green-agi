# Phase 3 — AaaS foundation (multi-tenancy, real auth, secret vault)

**Goal:** make the platform safely hold *more than one brand*. → unlocks Goal 3.

**Precondition:** Phases 0–1 (single Postgres, live). Best started once Goal 1 is
proven so the agent logic is stable before multi-tenant complexity lands.

**Effort:** several sessions. This is the expensive, retrofit-sensitive work —
doing it before there's a second tenant is fine *only* because it's a known
prerequisite, not speculation.

---

## Task 3.1 — `orgId` on every business model
- Add `orgId String` (FK → `Org`) to: Post, AdCampaign, InsightsCache, Creative,
  Influencer, InfluencerConversation, HashtagUsage, Order, AdSpendDaily,
  Attribution, ApprovalQueue, Job, AuditLog. Index each `@@index([orgId])`.
- Backfill existing rows to the More Green org. Migration.
- **Acceptance:** every business table has a non-null `orgId` after backfill.

## Task 3.2 — Enforce scoping (defense in depth)
- **Web**: a Prisma client extension/middleware that injects
  `where: { orgId: currentOrg }` on every find/update/delete and sets `orgId`
  on create, derived from the authenticated user's org (never from the request
  body). No route should hand-roll org filters.
- **Pipeline**: `process_jobs` and every command take an `orgId` (or iterate
  orgs) so a tenant's cron work only touches its rows.
- **Acceptance:** an integration test proves user in org A cannot read/mutate an
  org B row even with a forged id (IDOR test).

## Task 3.3 — Real auth provider
- Replace the shared-password login with **Auth.js** (email magic-link or
  OAuth). `getCurrentUser` swaps the cookie lookup for `getServerSession`;
  `requireRole` and all route guards stay unchanged (seam already built).
- Add session expiry/rotation; remove `DEV_ROLE` and `ADMIN_PASSWORD` from prod.
- Add a real `/login` + `/signup` UI.
- **Acceptance:** users sign in without a shared secret; sessions expire; guards
  still enforce roles.

## Task 3.4 — Per-tenant secret vault
- Customers' Meta/Shopify/etc. credentials must NOT live in global env.
- New `TenantSecret` model: `orgId`, `provider`, `ciphertext`, `iv` — encrypted
  at rest with a server `ENCRYPTION_KEY` (libsodium/`node:crypto` AES-GCM).
- `config.py` / clients resolve credentials **per org** at job time, not from
  process env (env stays only for platform-level keys like Anthropic).
- **Acceptance:** two orgs with different Meta tokens run jobs against their own
  ad accounts; secrets are unreadable at rest.

## Task 3.5 — Org-aware dashboard
- Org switcher (for staff/agency view), per-org data everywhere, org settings
  page (members, roles, connected accounts).
- **Acceptance:** switching org changes all screens; inviting a member works.

---

## Risks & mitigations
- **IDOR / cross-tenant leak** (the whole point) → middleware-enforced scoping +
  an explicit IDOR test suite; never trust `orgId` from the client.
- **Retrofit churn** → land `orgId` + middleware in one migration/PR to avoid a
  half-scoped window.
- **Secret encryption key management** → store `ENCRYPTION_KEY` in host secret
  store; document rotation.
- **Pipeline fan-out cost** → per-org cron multiplies API calls; add per-org
  caps before onboarding many tenants (ties into Phase 4 metering).

## Definition of done
Two isolated orgs can coexist with enforced data separation, real auth, and
per-tenant credentials. Platform is *safe* to onboard a paying customer.
