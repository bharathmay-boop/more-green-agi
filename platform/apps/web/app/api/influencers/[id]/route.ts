// /api/influencers/[id] — update status / pipeline stage (E8-T1).
import { NextResponse } from "next/server";
import { prisma, writeAudit } from "@/lib/db";
import { requireRole } from "@/lib/auth";

export const dynamic = "force-dynamic";

const STATUSES = new Set(["discovered", "contacted", "replied", "negotiating", "agreed", "posted", "declined"]);

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const gate = await requireRole("approver");
  if (gate instanceof Response) return gate;
  const { id } = await params;
  const nid = Number(id);
  if (!Number.isInteger(nid) || nid <= 0) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }
  const body = await req.json().catch(() => ({}));
  const status = String(body.status || "");
  if (!STATUSES.has(status)) {
    return NextResponse.json({ error: `status must be one of ${[...STATUSES].join(", ")}` }, { status: 400 });
  }
  try {
    const before = await prisma.influencer.findUnique({ where: { id: nid }, select: { status: true } });
    const influencer = await prisma.influencer.update({ where: { id: nid }, data: { status } });
    const actor = gate.email;
    await writeAudit({
      actor, action: "status_change", entity: "influencer", entityId: nid,
      before: { status: before?.status }, after: { status },
    });
    return NextResponse.json({ influencer });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 404 });
  }
}
