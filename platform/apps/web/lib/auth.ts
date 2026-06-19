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
import { cookies } from "next/headers";
import { prisma, safeQuery } from "@/lib/db";

export type Role = "owner" | "approver" | "viewer";

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
  const email = jar.get("mg_session")?.value;

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
