// /api/influencers/[id] — update status / pipeline stage (E8-T1).
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export const dynamic = "force-dynamic";

const STATUSES = new Set(["discovered", "contacted", "replied", "negotiating", "agreed", "posted", "declined"]);

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await req.json().catch(() => ({}));
  const status = String(body.status || "");
  if (!STATUSES.has(status)) {
    return NextResponse.json({ error: `status must be one of ${[...STATUSES].join(", ")}` }, { status: 400 });
  }
  try {
    const influencer = await prisma.influencer.update({ where: { id: Number(id) }, data: { status } });
    return NextResponse.json({ influencer });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 404 });
  }
}
