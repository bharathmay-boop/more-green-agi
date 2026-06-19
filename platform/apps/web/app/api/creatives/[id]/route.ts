// /api/creatives/[id] — select / reject a variant, or regenerate (E1-T8).
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { enqueueJob } from "@/lib/queue";
import { requireRole } from "@/lib/auth";

export const dynamic = "force-dynamic";

const ALLOWED = new Set(["selected", "rejected", "ready"]);

// PATCH { status } — select/reject a creative variant.
export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const gate = await requireRole("approver");
  if (gate instanceof Response) return gate;
  const { id } = await params;
  const body = await req.json().catch(() => ({}));
  const status = String(body.status || "");
  if (!ALLOWED.has(status)) {
    return NextResponse.json({ error: `status must be one of ${[...ALLOWED].join(", ")}` }, { status: 400 });
  }
  try {
    const creative = await prisma.creative.update({ where: { id: Number(id) }, data: { status } });
    return NextResponse.json({ creative });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 404 });
  }
}

// POST — enqueue a regeneration job for this creative's post.
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const gate = await requireRole("approver");
  if (gate instanceof Response) return gate;
  const { id } = await params;
  try {
    const creative = await prisma.creative.findUnique({ where: { id: Number(id) } });
    if (!creative) return NextResponse.json({ error: "not found" }, { status: 404 });
    const job = await enqueueJob("generate", { postId: creative.postId, regenerate: true });
    return NextResponse.json({ enqueued: job.id });
  } catch (err) {
    return NextResponse.json({ error: `queue unavailable: ${err}` }, { status: 503 });
  }
}
