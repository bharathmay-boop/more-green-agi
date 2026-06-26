// GET /api/health — liveness/readiness probe. Checks Postgres. 200 when
// reachable, 503 otherwise. For uptime monitors and LB probes. (No queue in
// Path A — the scheduled pipeline runs the agent; see plans/01 D1.)
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const db = await prisma.$queryRaw`SELECT 1`.then(() => true).catch(() => false);
  return NextResponse.json(
    { ok: db, db, time: new Date().toISOString() },
    { status: db ? 200 : 503 },
  );
}
