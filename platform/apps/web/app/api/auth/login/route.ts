// POST /api/auth/login {email, password}  ·  POST .../logout
//
// Interim operator login: verifies a single shared ADMIN_PASSWORD (constant-time)
// and that the email exists in the users table, then sets an HMAC-signed
// mg_session cookie. Role is resolved from the DB on each request by
// getCurrentUser — the cookie only proves "this email authenticated".
//
// ponytail: shared-password, single-operator login. Replace with Auth.js (per-user
// credentials, expiry, rotation) when external users log in — getCurrentUser and
// the route guards stay unchanged.
import { timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { signSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

function passwordOk(given: string): boolean {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) return false; // no password configured => login disabled
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function POST(req: Request) {
  if (!process.env.SESSION_SECRET) {
    return NextResponse.json({ error: "auth not configured (SESSION_SECRET unset)" }, { status: 503 });
  }
  const body = await req.json().catch(() => ({}));
  const email = String(body.email || "").trim().toLowerCase();
  const password = String(body.password || "");

  // Constant-time password check regardless of whether the user exists, so the
  // response time doesn't reveal valid emails.
  const ok = passwordOk(password);
  const user = email
    ? await prisma.user.findUnique({ where: { email } }).catch(() => null)
    : null;

  if (!ok || !user) {
    return NextResponse.json({ error: "invalid credentials" }, { status: 401 });
  }

  const res = NextResponse.json({ email: user.email, role: user.role });
  res.cookies.set("mg_session", signSession(user.email), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 12, // 12h
  });
  return res;
}
