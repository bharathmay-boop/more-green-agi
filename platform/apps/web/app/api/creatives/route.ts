// /api/creatives — list generated creative variants (E1-T8).
import { NextResponse } from "next/server";
import { prisma, safeQuery } from "@/lib/db";
import { requireSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const gate = await requireSession();
  if (gate instanceof Response) return gate;
  const postId = new URL(req.url).searchParams.get("postId");
  const creatives = await safeQuery(
    () => prisma.creative.findMany({
      where: postId ? { postId } : undefined,
      orderBy: [{ postId: "asc" }, { variantIndex: "asc" }],
      take: 300,
    }),
    [],
  );
  return NextResponse.json({ creatives });
}
