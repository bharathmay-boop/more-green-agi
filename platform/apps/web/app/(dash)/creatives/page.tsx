import { prisma, safeQuery } from "@/lib/db";
import { PageHeader, Empty } from "../_components/ui";
import { CreativeCard } from "./CreativeCard";

export const dynamic = "force-dynamic";

export default async function CreativesPage() {
  const [creatives, posts] = await Promise.all([
    safeQuery(
      () => prisma.creative.findMany({ orderBy: [{ postId: "asc" }, { variantIndex: "asc" }] }),
      [] as Awaited<ReturnType<typeof prisma.creative.findMany>>,
    ),
    safeQuery(
      () => prisma.post.findMany({ select: { postId: true, imagePrompt: true, videoPrompt: true, contentPillar: true } }),
      [] as { postId: string; imagePrompt: string | null; videoPrompt: string | null; contentPillar: string | null }[],
    ),
  ]);

  const promptByPost = Object.fromEntries(posts.map((p) => [p.postId, p]));

  const byPost = creatives.reduce<Record<string, typeof creatives>>((acc, c) => {
    (acc[c.postId] ??= []).push(c);
    return acc;
  }, {});

  return (
    <section>
      <PageHeader
        title="Creative Review"
        subtitle="AI-generated image and video variants. Select the winner for each post or reject to regenerate."
      />

      {creatives.length === 0 ? (
        <Empty>No creatives yet — the agent generates these after posts are approved for production. Check back after the next pipeline run.</Empty>
      ) : (
        Object.entries(byPost).map(([postId, items]) => {
          const meta = promptByPost[postId];
          return (
            <div key={postId} style={{ marginBottom: 24 }}>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4, color: "var(--mg-text)" }}>{postId}</div>
              {meta?.contentPillar && (
                <div style={{ fontSize: 12, color: "var(--mg-muted)", marginBottom: 4 }}>{meta.contentPillar}</div>
              )}
              {(meta?.imagePrompt || meta?.videoPrompt) && (
                <details style={{ marginBottom: 10 }}>
                  <summary style={{ fontSize: 12, color: "var(--mg-muted)", cursor: "pointer" }}>Show prompt</summary>
                  <pre style={{ fontSize: 12, color: "var(--mg-muted)", margin: "4px 0 0", whiteSpace: "pre-wrap", overflowWrap: "break-word" }}>
                    {meta.imagePrompt || meta.videoPrompt}
                  </pre>
                </details>
              )}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
                {items.map((c) => (
                  <CreativeCard key={c.id} creative={c} />
                ))}
              </div>
            </div>
          );
        })
      )}
    </section>
  );
}
