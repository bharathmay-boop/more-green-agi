// Audit log screen — append-only who/what/when/before→after (B2B audit, item #1).
import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, Card, Badge, Empty, toneFor, td, th } from "../_components/ui";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const rows = await safeQuery(
    () => prisma.auditLog.findMany({ orderBy: { createdAt: "desc" }, take: 500 }),
    [],
  );

  return (
    <section>
      <PageHeader
        title="Audit"
        subtitle="Append-only log of every state-changing action (who · what · when · before→after). Written on approvals and influencer status changes."
      />
      {rows.length === 0 ? (
        <Empty>No audit entries yet. Approve a proposal or change an influencer status to populate.</Empty>
      ) : (
        <Card>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>When</th><th style={th}>Actor</th><th style={th}>Action</th>
                <th style={th}>Entity</th><th style={th}>Before → After</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td style={td}>{r.createdAt.toLocaleString("en-IN")}</td>
                  <td style={td}>{r.actor ?? "—"}</td>
                  <td style={td}><Badge tone={toneFor(r.action ?? "")}>{r.action ?? "—"}</Badge></td>
                  <td style={td}>{r.entity}#{r.entityId}</td>
                  <td style={{ ...td, fontFamily: "monospace", fontSize: 12 }}>
                    {(r.beforeJson ?? "∅")} → {(r.afterJson ?? "∅")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  );
}
