// Creative Review screen (E1-T8) — variants grouped by post with status + score.
import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, Card, Badge, Empty, toneFor, td, th } from "../_components/ui";

export const dynamic = "force-dynamic";

export default async function CreativesPage() {
  const creatives = await safeQuery(
    () => prisma.creative.findMany({ orderBy: [{ postId: "asc" }, { variantIndex: "asc" }], take: 300 }),
    [] as Awaited<ReturnType<typeof prisma.creative.findMany>>,
  );

  const byPost = new Map<string, typeof creatives>();
  for (const c of creatives) {
    if (!byPost.has(c.postId)) byPost.set(c.postId, []);
    byPost.get(c.postId)!.push(c);
  }

  return (
    <section>
      <PageHeader
        title="Creative Review"
        subtitle="AI-generated image and video variants. Select the winner for each post or reject to regenerate."
      />
      {creatives.length === 0 ? (
        <Empty>No creatives yet — the agent generates these after posts are approved for production. Check back after the next pipeline run.</Empty>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {[...byPost.entries()].map(([postId, items]) => (
            <Card key={postId}>
              <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>{postId}</div>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr><th style={th}>Variant</th><th style={th}>Kind</th><th style={th}>Status</th><th style={th}>Score</th><th style={th}>Cost $</th></tr>
                </thead>
                <tbody>
                  {items.map((c) => (
                    <tr key={c.id}>
                      <td style={td}>#{c.variantIndex}</td>
                      <td style={td}>{c.kind}</td>
                      <td style={td}><Badge tone={toneFor(c.status)}>{c.status}</Badge></td>
                      <td style={td}>{c.score == null ? "—" : c.score.toFixed(2)}</td>
                      <td style={td}>{c.costUsd == null ? "—" : c.costUsd.toFixed(3)}</td>
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
