# Phase 4 — Monetization (onboarding OAuth + billing)

**Goal:** a customer can self-serve sign up, connect their own accounts, and pay.
→ Goal 3 sellable.

**Precondition:** Phase 3 (multi-tenancy, auth, secret vault).

**Effort:** several sessions. The onboarding OAuth is the make-or-break; billing
is comparatively standard.

---

## Task 4.1 — Self-serve onboarding with per-tenant OAuth  ⭐ make-or-break
- **Meta**: implement the Facebook Login + Marketing API OAuth flow so a customer
  grants access to *their* ad account / page / IG — store tokens in the Phase-3
  `TenantSecret` vault. Handle token refresh + scope/permission errors.
- **Shopify**: OAuth app install flow → per-store access token in the vault.
- Guided setup wizard: connect Meta → connect Shopify → pick SKUs → set caps →
  go. This wizard *is* the product; without it AaaS can't exist.
- **Acceptance:** a brand-new org, starting from zero, connects its own Meta +
  Shopify and runs its first generate→approve loop without any platform-admin
  intervention.

## Task 4.2 — Plans, billing, metering (Stripe)
- Stripe products/prices for tiers; checkout + customer portal.
- Meter usage that costs money to serve: creative generations (fal/BytePlus),
  Anthropic tokens, ad-spend volume. Store per-org monthly counters.
- Enforce plan limits: block generation / apply when over plan; surface usage in
  the dashboard.
- **Acceptance:** subscribing unlocks limits; exceeding a plan blocks the metered
  action with a clear upgrade prompt; webhooks keep status in sync.

## Task 4.3 — Tenant lifecycle
- Trial → active → past_due → canceled handling; data retention on cancel;
  re-activation.
- **Acceptance:** a canceled org loses access but data is retained per policy;
  re-subscribing restores it.

## Task 4.4 — Trust & compliance basics for selling
- Per-tenant audit export, a privacy policy + DPA, Meta/Shopify app review
  submissions (required for production OAuth scopes).
- Add Sentry (deferred item) once real customers exist — first opaque incident
  justifies it.
- **Acceptance:** Meta/Shopify apps approved for production; audit export works.

---

## Risks & mitigations
- **Meta/Shopify app review** can take weeks and gate launch → start review early
  (parallel with Phase 3); design scopes minimally.
- **Token expiry/permission revocation** mid-campaign → robust refresh + clear
  "reconnect your account" UX; never silently fail a spend action.
- **Metering accuracy vs money** → meter at the same gate that triggers spend;
  reconcile against provider invoices.
- **Abuse / runaway spend by a tenant** → per-org hard caps (reuse the existing
  cap machinery, scoped per org).

## Definition of done
A stranger can sign up, connect their own Meta + Shopify, subscribe, and run the
agent on their brand — within metered limits. **Goal 3 = sellable.**
