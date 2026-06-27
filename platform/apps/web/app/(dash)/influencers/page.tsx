// Influencer CRM screen (E8-T1) — discovered creators + pipeline status.
import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, Card, Badge, Empty, toneFor, td, th } from "../_components/ui";

export const dynamic = "force-dynamic";

export default async function InfluencersPage() {
  const influencers = await safeQuery(
    () => prisma.influencer.findMany({
      orderBy: { followers: "desc" },
      include: { _count: { select: { conversations: true } } },
      take: 500,
    }),
    [],
  );

  const byStatus = influencers.reduce<Record<string, number>>((acc, i) => {
    acc[i.status] = (acc[i.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <section>
      <PageHeader
        title="Influencers"
        subtitle="Discovered creators and outreach pipeline. Update status via PATCH /api/influencers/[id]. Source: chrome-find-influencers + the outreach agent."
      />
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {Object.entries(byStatus).map(([s, n]) => (
          <Badge key={s} tone={toneFor(s)}>{s}: {n}</Badge>
        ))}
      </div>
      {influencers.length === 0 ? (
        <Empty>No influencers discovered yet. The agent discovers these during pipeline runs.</Empty>
      ) : (
        <Card>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr><th style={th}>Username</th><th style={th}>Name</th><th style={th}>Followers</th><th style={th}>Msgs</th><th style={th}>Status</th></tr>
            </thead>
            <tbody>
              {influencers.map((i) => (
                <tr key={i.id}>
                  <td style={td}>@{i.username}</td>
                  <td style={td}>{i.fullName || "—"}</td>
                  <td style={td}>{i.followers?.toLocaleString("en-IN") ?? "—"}</td>
                  <td style={td}>{i._count.conversations}</td>
                  <td style={td}><Badge tone={toneFor(i.status)}>{i.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  );
}
