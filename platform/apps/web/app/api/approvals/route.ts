// /api/approvals — list proposals in the approval queue (E3-T4).
import { NextResponse } from "next/server";
import { prisma, safeQuery } from "@/lib/db";
import { requireSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const gate = await requireSession();
  if (gate instanceof Response) return gate;
  const status = new URL(req.url).searchParams.get("status") || undefined;
  const items = await safeQuery(
    () => prisma.approvalQueue.findMany({
      where: status ? { status } : undefined,
      orderBy: { requestedAt: "desc" },
      take: 200,
    }),
    [],
  );
  return NextResponse.json({ items });
}
