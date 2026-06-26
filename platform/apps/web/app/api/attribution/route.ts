// /api/attribution — ROAS rollups by scope + date range (E2-T4).
import { NextResponse } from "next/server";
import { prisma, safeQuery } from "@/lib/db";
import { requireSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const gate = await requireSession();
  if (gate instanceof Response) return gate;
  const sp = new URL(req.url).searchParams;
  const scope = sp.get("scope") || "sku";            // sku | campaign | blended
  const days = Math.max(1, Math.min(365, Number(sp.get("days") || 30)));
  const start = new Date(Date.now() - days * 86400_000).toISOString().slice(0, 10);

  const rows = await safeQuery(
    () => prisma.attribution.findMany({
      where: { scope, date: { gte: start } },
      orderBy: [{ date: "desc" }, { scopeId: "asc" }],
      take: 500,
    }),
    [],
  );
  return NextResponse.json({ scope, days, rows });
}
