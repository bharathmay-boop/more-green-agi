// GET /api/health — liveness/readiness probe. Checks Postgres + Redis.
// 200 when both reachable, 503 otherwise. For uptime monitors and LB probes.
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { isQueueHealthy } from "@/lib/queue";

export const dynamic = "force-dynamic";

export async function GET() {
  const [db, redis] = await Promise.all([
    prisma.$queryRaw`SELECT 1`.then(() => true).catch(() => false),
    isQueueHealthy(),
  ]);
  const ok = db && redis;
  return NextResponse.json(
    { ok, db, redis, time: new Date().toISOString() },
    { status: ok ? 200 : 503 },
  );
}
