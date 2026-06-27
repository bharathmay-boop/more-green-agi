import Link from "next/link";
import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, SectionCard, Stat, Badge, toneFor, Empty } from "./_components/ui";

export const dynamic = "force-dynamic";

const ROAS_FLOOR = 2.5;

function fmt(n: number) {
  return "₹" + n.toLocaleString("en-IN");
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export default async function HomePage() {
  const today = todayISO();

  const [pendingCount, postGroups, todayAttr, recentActivity] = await Promise.all([
    safeQuery(
      () => prisma.approvalQueue.count({ where: { status: { in: ["pending", "approved"] } } }),
      0,
    ),
    safeQuery(
      () => prisma.post.groupBy({ by: ["pipelineStatus"], _count: { _all: true } }),
      [] as { pipelineStatus: string | null; _count: { _all: number } }[],
    ),
    safeQuery(
      () => prisma.attribution.findMany({ where: { scope: "sku", date: { gte: today } }, take: 100 }),
      [] as Awaited<ReturnType<typeof prisma.attribution.findMany>>,
    ),
    safeQuery(
      () => prisma.auditLog.findMany({ take: 8, orderBy: { createdAt: "desc" } }),
      [] as Awaited<ReturnType<typeof prisma.auditLog.findMany>>,
    ),
  ]);

  const postsByStatus = Object.fromEntries(
    postGroups.map((g) => [g.pipelineStatus ?? "unknown", g._count._all]),
  );
  const totalPosts = postGroups.reduce((s, g) => s + g._count._all, 0);

  const todaySpend = todayAttr.reduce((s, r) => s + r.spendInr, 0);
  const todayRev = todayAttr.reduce((s, r) => s + r.revenueInr, 0);
  const todayRoas = todaySpend > 0 ? (todayRev / todaySpend).toFixed(2) + "×" : "—";

  const STATUS_ORDER = ["draft", "creative_ready", "scheduled", "published", "failed"];
  const allStatuses = [...new Set([...STATUS_ORDER, ...Object.keys(postsByStatus)])];

  return (
    <section>
      <PageHeader
        title="Morning Briefing"
        subtitle={`More Green dashboard — ${new Date().toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}`}
      />

      {/* Key metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
        {[
          { label: "Pending approvals", value: String(pendingCount), tone: pendingCount > 0 ? "amber" : "green", href: "/approvals" } as const,
          { label: "Posts in pipeline", value: String(totalPosts), tone: "gray", href: "/calendar" } as const,
          { label: "Today spend", value: todaySpend > 0 ? fmt(todaySpend) : "—", tone: "gray", href: "/roas" } as const,
          { label: "Today ROAS", value: todayRoas, tone: todaySpend > 0 && todayRev / todaySpend >= ROAS_FLOOR ? "green" : todaySpend > 0 ? "red" : "gray", href: "/roas" } as const,
        ].map((m) => (
          <Link key={m.label} href={m.href} style={{ textDecoration: "none" }}>
            <div style={{ border: "1px solid var(--mg-border)", borderRadius: 10, background: "var(--mg-surface)", padding: 16 }}>
              <Stat label={m.label} value={m.value} tone={m.tone} />
            </div>
          </Link>
        ))}
      </div>

      {/* Pipeline status */}
      <SectionCard title="Pipeline status" action={<Link href="/calendar" style={{ fontSize: 12, color: "var(--mg-muted)", textDecoration: "none" }}>View calendar →</Link>}>
        {totalPosts === 0 ? (
          <p style={{ margin: 0, fontSize: 13, color: "var(--mg-muted)" }}>No posts yet — the agent creates them during pipeline runs.</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {allStatuses
              .filter((s) => postsByStatus[s] != null)
              .map((s) => (
                <div key={s} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                  <Badge tone={toneFor(s)}>{s}</Badge>
                  <span style={{ fontWeight: 600, color: "var(--mg-text)" }}>{postsByStatus[s]}</span>
                </div>
              ))}
          </div>
        )}
      </SectionCard>

      {/* Pending proposals call-to-action */}
      {pendingCount > 0 && (
        <div style={{ border: "1px solid #f3c06d", borderRadius: 10, background: "#fdf8ee", padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: "#7a5200" }}>
            {pendingCount} agent proposal{pendingCount !== 1 ? "s" : ""} waiting for your decision
          </span>
          <Link href="/approvals" style={{ fontSize: 13, fontWeight: 600, color: "#08a045", textDecoration: "none" }}>Review →</Link>
        </div>
      )}

      {/* Recent activity */}
      <SectionCard title="Recent activity" action={<Link href="/audit" style={{ fontSize: 12, color: "var(--mg-muted)", textDecoration: "none" }}>Full log →</Link>}>
        {recentActivity.length === 0 ? (
          <p style={{ margin: 0, fontSize: 13, color: "var(--mg-muted)" }}>No activity yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {recentActivity.map((r, idx) => (
              <div key={r.id} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 0", borderBottom: idx < recentActivity.length - 1 ? "1px solid var(--mg-border)" : undefined }}>
                <Badge tone={toneFor(r.action ?? "")}>{r.action ?? "—"}</Badge>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 13, color: "var(--mg-text)" }}>{r.entity}#{r.entityId}</span>
                  {r.actor && <span style={{ fontSize: 12, color: "var(--mg-muted)", marginLeft: 6 }}>by {r.actor}</span>}
                </div>
                <div style={{ fontSize: 11, color: "var(--mg-muted)", whiteSpace: "nowrap" }}>
                  {r.createdAt.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </section>
  );
}
