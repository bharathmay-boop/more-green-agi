# Phase 2 — Portfolio packaging

**Goal:** turn the live system into a credible, clickable portfolio piece. → Goal 2.

**Precondition:** Phase 1 live (real URL, real data).

**Effort:** ~half a session. Mostly packaging, minimal engineering.

---

## Task 2.1 — Case-study README (`platform/README.md` / public page)
- Narrative: problem (a founder can't run marketing full-time) → solution (an
  autonomous marketing agent) → architecture (agent loop, money-safety gate,
  RBAC, audit trail) → results (real metrics from `/roas`).
- Include an architecture diagram (the 9 job types + approval gate + cron).
- **Acceptance:** a non-technical reader understands what it does in 60s; a
  technical reader sees the design depth.

## Task 2.2 — Read-only demo account
- Seed a `viewer` user (`demo@moregreen…`) + publish the password in the case
  study, OR a `/demo` route that auto-issues a signed viewer cookie.
- Viewer role already blocks every mutation (RBAC verified) → safe to share
  publicly.
- Optionally point demo at a **seeded sample org** with realistic-but-fake data
  so real spend/PII isn't exposed.
- **Acceptance:** anyone can log in as viewer, click all screens, and cannot
  approve/apply/post (403).

## Task 2.3 — Walkthrough asset (optional)
- 2–3 min Loom: calendar → creative review → approvals (money-safety) → ROAS →
  audit log.
- **Acceptance:** linked from the README.

## Task 2.4 — Polish pass
- Empty-state copy, favicon/title, a simple `/login` form (so demo users don't
  need the console — small, also useful for Phase 1).
- **Acceptance:** no raw stack traces, no dev placeholders on any screen.

---

## Risks
- **Leaking real brand data/spend** in a public demo → use the seeded sample org
  + viewer role; never expose the real `ADMIN_PASSWORD`.

## Definition of done
A shareable URL + case study + safe demo login. **Goal 2 = done.**
