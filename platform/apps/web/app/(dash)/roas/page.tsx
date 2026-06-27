// ROAS dashboard (E2-T4) — blended vs paid ROAS per SKU over a window, with
// spend/revenue aggregation and a below-floor highlight.
import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, Card, Badge, Empty, td, th } from "../_components/ui";

export const dynamic = "force-dynamic";

const ROAS_FLOOR = 2.5; // mirrors config.ROAS_FLOOR_FOR_SCALE

export default async function RoasPage() {
  const start = new Date(Date.now() - 30 * 86400_000).toISOString().slice(0, 10);
  const rows = await safeQuery(
    () => prisma.attribution.findMany({ where: { scope: "sku", date: { gte: start } }, take: 1000 }),
    [] as Awaited<ReturnType<typeof prisma.attribution.findMany>>,
  );

  // aggregate per SKU across the window
  const agg = new Map<string, { spend: number; revenue: number }>();
  for (const r of rows) {
    const a = agg.get(r.scopeId) || { spend: 0, revenue: 0 };
    a.spend += r.spendInr;
    a.revenue += r.revenueInr;
    agg.set(r.scopeId, a);
  }
  const skus = [...agg.entries()]
    .map(([sku, a]) => ({ sku, ...a, roas: a.spend ? a.revenue / a.spend : null }))
    .sort((x, y) => (y.roas ?? -1) - (x.roas ?? -1));

  const totalSpend = skus.reduce((s, x) => s + x.spend, 0);
  const totalRev = skus.reduce((s, x) => s + x.revenue, 0);

  return (
    <section>
      <PageHeader
        title="ROAS"
        subtitle={`Paid ROAS by SKU, last 30 days. Below the ${ROAS_FLOOR}× scale floor is flagged. Source: /api/attribution.`}
      />
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <Card style={{ flex: 1 }}><div style={{ color: "var(--mg-muted)", fontSize: 12 }}>Spend (30d)</div><div style={{ fontSize: 22, fontWeight: 600 }}>₹{totalSpend.toLocaleString("en-IN")}</div></Card>
        <Card style={{ flex: 1 }}><div style={{ color: "var(--mg-muted)", fontSize: 12 }}>Revenue (30d)</div><div style={{ fontSize: 22, fontWeight: 600 }}>₹{totalRev.toLocaleString("en-IN")}</div></Card>
        <Card style={{ flex: 1 }}><div style={{ color: "var(--mg-muted)", fontSize: 12 }}>Paid ROAS</div><div style={{ fontSize: 22, fontWeight: 600 }}>{totalSpend ? (totalRev / totalSpend).toFixed(2) + "×" : "—"}</div></Card>
      </div>
      {skus.length === 0 ? (
        <Empty>No attribution yet. Run sync-orders + monitor-ads + compute-attribution.</Empty>
      ) : (
        <Card>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr><th style={th}>SKU</th><th style={th}>Spend ₹</th><th style={th}>Revenue ₹</th><th style={th}>Paid ROAS</th><th style={th}>Health</th></tr>
            </thead>
            <tbody>
              {skus.map((s) => (
                <tr key={s.sku}>
                  <td style={td}>{s.sku}</td>
                  <td style={td}>{s.spend.toLocaleString("en-IN")}</td>
                  <td style={td}>{s.revenue.toLocaleString("en-IN")}</td>
                  <td style={td}>{s.roas == null ? "—" : s.roas.toFixed(2) + "×"}</td>
                  <td style={td}>
                    {s.roas == null ? <Badge tone="gray">no spend</Badge>
                      : s.roas >= ROAS_FLOOR ? <Badge tone="green">scale-ready</Badge>
                      : <Badge tone="red">below floor</Badge>}
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
