// /api/influencers — list influencers with conversation counts (E8-T1).
import { NextResponse } from "next/server";
import { prisma, safeQuery } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const status = new URL(req.url).searchParams.get("status") || undefined;
  const influencers = await safeQuery(
    () => prisma.influencer.findMany({
      where: status ? { status } : undefined,
      orderBy: { followers: "desc" },
      include: { _count: { select: { conversations: true } } },
      take: 500,
    }),
    [],
  );
  return NextResponse.json({ influencers });
}
