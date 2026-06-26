// /api/approvals/[id] — approve / reject / apply a proposal (E3-T4).
//
// MONEY-SAFETY (doc 04): this route NEVER calls Meta. "approve"/"reject" are
// pure status transitions; "apply" only marks an already-approved row as ready —
// the scheduled `apply-approved` job (automation/commands/apply_approved.py) is
// the single code path allowed to raise spend, after a cap re-check. Illegal
// transitions are rejected here, mirroring automation/utils/approvals.py.
import { NextResponse } from "next/server";
import { prisma, writeAudit } from "@/lib/db";
import { requireRole } from "@/lib/auth";

export const dynamic = "force-dynamic";

type Action = "approve" | "reject" | "apply";

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  // RBAC (E9-T1): approving/applying spend is approver|owner only.
  const gate = await requireRole("approver");
  if (gate instanceof Response) return gate;

  const { id } = await params;
  const pid = Number(id);
  if (!Number.isInteger(pid) || pid <= 0) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }
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
    await writeAudit({
      actor, action, entity: "approval_queue", entityId: pid,
      before: { status: row.status }, after: { status: updated.status },
    });
    return NextResponse.json({ item: updated });
  }

  // action === "apply": valid only from approved. Path A has no always-on
  // worker — the scheduled apply-approved run applies every approved row after a
  // cap re-check. So "apply" records intent; the spend still happens only in
  // Python. (On-demand apply returns with the job queue in Phase 3/4 — plans/01.)
  if (row.status !== "approved") {
    return NextResponse.json(
      { error: `cannot apply: row is '${row.status}', expected 'approved'` }, { status: 409 });
  }
  await writeAudit({
    actor, action: "apply", entity: "approval_queue", entityId: pid,
    before: { status: "approved" }, after: { status: "approved", note: "queued for scheduled apply-approved" },
  });
  return NextResponse.json({
    ok: true,
    note: "approved — the scheduled apply-approved run will apply this after a cap re-check",
  });
}
