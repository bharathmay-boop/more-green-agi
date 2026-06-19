// /api/approvals/[id] — approve / reject / apply a proposal (E3-T4).
//
// MONEY-SAFETY (doc 04): this route NEVER calls Meta. "approve"/"reject" are
// pure status transitions; "apply" only ENQUEUES the apply_approved worker job,
// which is the single code path allowed to raise spend — and only after the row
// is in `approved` state. Illegal transitions are rejected here, mirroring the
// Python state machine in automation/utils/approvals.py.
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { enqueueJob } from "@/lib/queue";
import { requireRole } from "@/lib/auth";

export const dynamic = "force-dynamic";

type Action = "approve" | "reject" | "apply";

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  // RBAC (E9-T1): approving/applying spend is approver|owner only.
  const gate = await requireRole("approver");
  if (gate instanceof Response) return gate;

  const { id } = await params;
  const pid = Number(id);
  const body = await req.json().catch(() => ({}));
  const action = body.action as Action;
  const actor = gate.email;

  if (!["approve", "reject", "apply"].includes(action)) {
    return NextResponse.json({ error: "action must be approve | reject | apply" }, { status: 400 });
  }

  const row = await prisma.approvalQueue.findUnique({ where: { id: pid } }).catch(() => null);
  if (!row) return NextResponse.json({ error: "not found" }, { status: 404 });

  // ── guarded transitions ──
  if (action === "approve" || action === "reject") {
    if (row.status !== "pending") {
      return NextResponse.json(
        { error: `cannot ${action}: row is '${row.status}', expected 'pending'` }, { status: 409 });
    }
    const updated = await prisma.approvalQueue.update({
      where: { id: pid },
      data: {
        status: action === "approve" ? "approved" : "rejected",
        decidedBy: actor,
        decidedAt: new Date(),
      },
    });
    return NextResponse.json({ item: updated });
  }

  // action === "apply": only valid from approved; enqueue the gated worker.
  if (row.status !== "approved") {
    return NextResponse.json(
      { error: `cannot apply: row is '${row.status}', expected 'approved'` }, { status: 409 });
  }
  try {
    const job = await enqueueJob("apply_approved", { approvalId: pid });
    return NextResponse.json({ enqueued: job.id, note: "apply_approved worker will apply after cap re-check" });
  } catch (err) {
    return NextResponse.json({ error: `queue unavailable: ${err}` }, { status: 503 });
  }
}
