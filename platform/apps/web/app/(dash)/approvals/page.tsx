// Approvals screen (E3-T4) — proposals awaiting a human decision.
// Approve/reject are status transitions; Apply enqueues the spend-gated worker.
import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, Card, Badge, Empty, toneFor, td, th } from "../_components/ui";
import { Actions } from "./Actions";

export const dynamic = "force-dynamic";

function impact(payload: string | null): string {
  if (!payload) return "";
  try {
    const p = JSON.parse(payload);
    if (p.current_inr != null && p.proposed_inr != null) return `₹${p.current_inr} → ₹${p.proposed_inr}`;
    if (p.current_price != null && p.proposed_price != null) return `₹${p.current_price} → ₹${p.proposed_price}`;
    if (p.sku) return String(p.sku);
    return "";
  } catch { return ""; }
}

export default async function ApprovalsPage() {
  const items = await safeQuery(
    () => prisma.approvalQueue.findMany({ orderBy: { requestedAt: "desc" }, take: 200 }),
    [] as Awaited<ReturnType<typeof prisma.approvalQueue.findMany>>,
  );
  const pending = items.filter((i) => i.status === "pending" || i.status === "approved");
  const history = items.filter((i) => !["pending", "approved"].includes(i.status));


  return (
    <section>
      <PageHeader
        title="Approvals"
        subtitle="Money/state proposals. Approving never spends — only the apply_approved worker raises budget, after a cap re-check (doc 04)."
      />
      {pending.length === 0 ? (
        <Empty>No pending proposals. tune-ads / strategize / storefront-propose produce them.</Empty>
      ) : (
        <Card style={{ marginBottom: 16 }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr><th style={th}>Action</th><th style={th}>Entity</th><th style={th}>Change</th><th style={th}>By</th><th style={th}>Status</th><th style={th}></th></tr>
            </thead>
            <tbody>
              {pending.map((i) => (
                <tr key={i.id}>
                  <td style={td}>{i.actionType}</td>
                  <td style={td}>{i.entityRef}</td>
                  <td style={td}>{impact(i.payloadJson)}</td>
                  <td style={td}>{i.requestedBy}</td>
                  <td style={td}><Badge tone={toneFor(i.status)}>{i.status}</Badge></td>
                  <td style={td}><Actions id={i.id} status={i.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {history.length > 0 && (
        <Card>
          <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>History</div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr><th style={th}>Action</th><th style={th}>Entity</th><th style={th}>Status</th><th style={th}>Error</th></tr>
            </thead>
            <tbody>
              {history.map((i) => (
                <tr key={i.id}>
                  <td style={td}>{i.actionType}</td>
                  <td style={td}>{i.entityRef}</td>
                  <td style={td}><Badge tone={toneFor(i.status)}>{i.status}</Badge></td>
                  <td style={{ ...td, color: "var(--mg-muted)" }}>{i.error || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  );
}
