// /api/posts — list + create content posts (E1-T7).
import { NextResponse } from "next/server";
import { prisma, safeQuery } from "@/lib/db";
import { requireRole } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  const posts = await safeQuery(
    () => prisma.post.findMany({ orderBy: { scheduledAt: "asc" }, take: 200 }),
    [],
  );
  return NextResponse.json({ posts });
}

export async function POST(req: Request) {
  const gate = await requireRole("approver");
  if (gate instanceof Response) return gate;
  const body = await req.json().catch(() => ({}));
  if (!body.postId || !body.sku) {
    return NextResponse.json({ error: "postId and sku are required" }, { status: 400 });
  }
  try {
    const post = await prisma.post.create({
      data: {
        postId: String(body.postId),
        sku: String(body.sku),
        scheduledAt: body.scheduledAt ?? null,
        platform: body.platform ?? "instagram",
        postType: body.postType ?? "feed_image",
        topic: body.topic ?? null,
        pipelineStatus: "draft",
      },
    });
    return NextResponse.json({ post }, { status: 201 });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
