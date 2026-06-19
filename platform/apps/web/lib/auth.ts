// Auth + RBAC (E9-T1).
//
// Roles: owner > approver > viewer. The money-sensitive actions (approve / apply
// in /api/approvals) are restricted to approver|owner; everyone else is read-only.
//
// This is the enforcement seam. `getCurrentUser` resolves the caller from a
// session cookie against the `users` table; wiring NextAuth/Auth.js later means
// only swapping the cookie lookup for a NextAuth session — the route guards
// (`requireRole`) stay unchanged. Secure by default: an unknown caller is a
// viewer, never an approver.
import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { prisma, safeQuery } from "@/lib/db";

export type Role = "owner" | "approver" | "viewer";

/**
 * Verify an HMAC-signed session cookie. Value format is `email.base64url(sig)`
 * where sig = HMAC-SHA256(email, SESSION_SECRET). An unsigned/forged/missing
 * signature returns null — the email field alone is NOT trusted (it's
 * attacker-controlled). Mint matching cookies server-side with `signSession`.
 *
 * No SESSION_SECRET set → no cookie can ever verify, so in production the
 * money-sensitive guards refuse to operate until a real auth provider is wired
 * (the DEV_ROLE escape hatch below is non-prod only).
 */
export function signSession(email: string): string {
  const secret = process.env.SESSION_SECRET;
  if (!secret) throw new Error("SESSION_SECRET not set");
  const sig = createHmac("sha256", secret).update(email).digest("base64url");
  return `${email}.${sig}`;
}

function verifySession(value: string | undefined): string | null {
  const secret = process.env.SESSION_SECRET;
  if (!value || !secret) return null;
  const dot = value.lastIndexOf(".");
  if (dot <= 0) return null;
  const email = value.slice(0, dot);
  const given = value.slice(dot + 1);
  const expected = createHmac("sha256", secret).update(email).digest("base64url");
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  return email;
}

const RANK: Record<Role, number> = { viewer: 0, approver: 1, owner: 2 };

export interface CurrentUser {
  email: string;
  role: Role;
  orgId: string | null;
}

const ANON: CurrentUser = { email: "anonymous", role: "viewer", orgId: null };

/**
 * Resolve the current user. Reads the `mg_session` cookie (email) and looks up
 * their role in the DB. A `DEV_ROLE` env var can elevate the local dev session
 * when there is no auth provider yet (never honoured in production).
 */
export async function getCurrentUser(): Promise<CurrentUser> {
  const jar = await cookies();
  const email = verifySession(jar.get("mg_session")?.value);

  if (email) {
    const user = await safeQuery(
      () => prisma.user.findUnique({ where: { email } }),
      null,
    );
    if (user) return { email: user.email, role: (user.role as Role) ?? "viewer", orgId: user.orgId };
  }

  if (process.env.NODE_ENV !== "production" && process.env.DEV_ROLE) {
    return { email: email ?? "dev@local", role: process.env.DEV_ROLE as Role, orgId: null };
  }
  return email ? { ...ANON, email } : ANON;
}

export function hasRole(user: CurrentUser, min: Role): boolean {
  return RANK[user.role] >= RANK[min];
}

/**
 * Guard for route handlers. Returns the user when authorised, or a 403 Response
 * to return directly when not. Usage:
 *
 *   const gate = await requireRole("approver");
 *   if (gate instanceof Response) return gate;
 */
export async function requireRole(min: Role): Promise<CurrentUser | Response> {
  const user = await getCurrentUser();
  if (!hasRole(user, min)) {
    return new Response(
      JSON.stringify({ error: `forbidden: requires ${min} role (you are ${user.role})` }),
      { status: 403, headers: { "content-type": "application/json" } },
    );
  }
  return user;
}
