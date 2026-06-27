// /api/creatives/[id] — select / reject a variant, or regenerate (E1-T8).
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
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
  } catch (err: unknown) {
    console.error(err);
    const is404 = typeof err === "object" && err !== null && (err as { code?: string }).code === "P2025";
    return NextResponse.json({ error: is404 ? "not found" : "could not update" }, { status: is404 ? 404 : 500 });
  }
}

// POST — on-demand regeneration. Deferred in Path A: there is no always-on
// worker, so regeneration happens on the scheduled `generate` run. On-demand
// regenerate returns with the job queue in Phase 3/4 (plans/01 D1).
export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const gate = await requireRole("approver");
  if (gate instanceof Response) return gate;
  const { id } = await params;
  const creative = await prisma.creative.findUnique({ where: { id: Number(id) } }).catch(() => null);
  if (!creative) return NextResponse.json({ error: "not found" }, { status: 404 });
  return NextResponse.json(
    { error: "on-demand regenerate is deferred; the scheduled generate run refreshes creatives" },
    { status: 501 },
  );
}
