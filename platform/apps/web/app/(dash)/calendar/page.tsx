// Calendar screen (E1-T7) — posts grouped by scheduled date with status badges.
import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, Card, Badge, Empty, toneFor, td, th } from "../_components/ui";

export const dynamic = "force-dynamic";

export default async function CalendarPage() {
  const posts = await safeQuery(
    () => prisma.post.findMany({ orderBy: { scheduledAt: "asc" }, take: 200 }),
    [] as Awaited<ReturnType<typeof prisma.post.findMany>>,
  );

  // group by scheduled date (or "Unscheduled")
  const groups = new Map<string, typeof posts>();
  for (const p of posts) {
    const key = (p.scheduledAt || "Unscheduled").slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(p);
  }

  return (
    <section>
      <PageHeader
        title="Calendar"
        subtitle="Scheduled content across SKUs. Status badges track each post through the pipeline; create posts via POST /api/posts, edit/hold/archive via PATCH /api/posts/[id]."
      />
      {posts.length === 0 ? (
        <Empty>No posts yet. Seed from SQLite or run the autopilot calendar.</Empty>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {[...groups.entries()].map(([date, items]) => (
            <Card key={date}>
              <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>{date}</div>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr><th style={th}>Post</th><th style={th}>SKU</th><th style={th}>Type</th><th style={th}>Platform</th><th style={th}>Status</th></tr>
                </thead>
                <tbody>
                  {items.map((p) => (
                    <tr key={p.postId}>
                      <td style={td}>{p.topic || p.postId}</td>
                      <td style={td}>{p.sku}</td>
                      <td style={td}>{p.postType}</td>
                      <td style={td}>{p.platform}</td>
                      <td style={td}><Badge tone={toneFor(p.pipelineStatus)}>{p.pipelineStatus}</Badge>{p.onHold ? <> <Badge tone="red">hold</Badge></> : null}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
