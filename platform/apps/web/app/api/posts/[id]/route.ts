// /api/posts/[id] — update / hold / archive a post (E1-T7).
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { requireRole } from "@/lib/auth";

export const dynamic = "force-dynamic";

const EDITABLE = new Set([
  "scheduledAt", "topic", "theme", "imagePrompt", "videoPrompt",
  "captionInstagram", "captionFacebook", "altText", "onHold",
  "promptsApproved", "creativesApproved", "pipelineStatus",
]);

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const gate = await requireRole("approver");
  if (gate instanceof Response) return gate;
  const { id } = await params;
  const body = await req.json().catch(() => ({}));
  const data: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(body)) {
    if (EDITABLE.has(k)) data[k] = v;
  }
  if (Object.keys(data).length === 0) {
    return NextResponse.json({ error: "no editable fields supplied" }, { status: 400 });
  }
  try {
    const post = await prisma.post.update({ where: { postId: id }, data });
    return NextResponse.json({ post });
  } catch (err: unknown) {
    console.error(err);
    const is404 = typeof err === "object" && err !== null && (err as { code?: string }).code === "P2025";
    return NextResponse.json({ error: is404 ? "not found" : "could not update" }, { status: is404 ? 404 : 500 });
  }
}

// Soft-delete = archive (on_hold). Hard delete is owner-only and not exposed here.
export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const gate = await requireRole("owner");
  if (gate instanceof Response) return gate;
  const { id } = await params;
  try {
    const post = await prisma.post.update({ where: { postId: id }, data: { onHold: true } });
    return NextResponse.json({ post });
  } catch (err: unknown) {
    console.error(err);
    const is404 = typeof err === "object" && err !== null && (err as { code?: string }).code === "P2025";
    return NextResponse.json({ error: is404 ? "not found" : "could not update" }, { status: is404 ? 404 : 500 });
  }
}
