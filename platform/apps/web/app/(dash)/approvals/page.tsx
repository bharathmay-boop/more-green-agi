import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, Badge, toneFor, Empty, td, th } from "../_components/ui";
import { ApprovalCard } from "./ApprovalCard";

export const dynamic = "force-dynamic";

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
        subtitle="Agent proposals awaiting your decision. Approving never spends — the apply-approved worker applies after a safety re-check."
      />

      {pending.length === 0 ? (
        <Empty>No pending proposals — the agent is working in the background and will surface new ones here.</Empty>
      ) : (
        <div style={{ border: "1px solid var(--mg-border)", borderRadius: 10, background: "var(--mg-surface)", overflow: "hidden", marginBottom: 16 }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--mg-border)", fontWeight: 600, fontSize: 13 }}>
            {pending.length} pending
          </div>
          {pending.map((i) => (
            <ApprovalCard key={i.id} item={i} />
          ))}
        </div>
      )}

      {history.length > 0 && (
        <div style={{ border: "1px solid var(--mg-border)", borderRadius: 10, background: "var(--mg-surface)", overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--mg-border)", fontWeight: 600, fontSize: 13, color: "var(--mg-muted)" }}>
            History
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>Action</th>
                <th style={th}>Entity</th>
                <th style={th}>Status</th>
                <th style={th}>Error</th>
              </tr>
            </thead>
            <tbody>
              {history.map((i) => (
                <tr key={i.id}>
                  <td style={td}>{i.actionType}</td>
                  <td style={td}>{i.entityRef}</td>
                  <td style={td}><Badge tone={toneFor(i.status)}>{i.status}</Badge></td>
                  <td style={{ ...td, color: "var(--mg-muted)", fontSize: 12 }}>{i.error || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
