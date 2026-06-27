import { NextRequest, NextResponse } from "next/server";
import { verifySession } from "@/lib/auth";

export const runtime = "nodejs";

export function middleware(req: NextRequest) {
  const email = verifySession(req.cookies.get("mg_session")?.value);
  if (!email) {
    return NextResponse.redirect(new URL("/login", req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|login|_next|favicon).*)"],
};
