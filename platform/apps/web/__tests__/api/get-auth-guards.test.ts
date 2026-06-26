// RED: these tests will fail until requireSession() is wired into every GET handler.
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/server", () => ({
  NextResponse: {
    json: (body: unknown, init?: ResponseInit) =>
      new Response(JSON.stringify(body), {
        status: (init as ResponseInit | undefined)?.status ?? 200,
        headers: { "content-type": "application/json" },
      }),
  },
}));

vi.mock("@/lib/db", () => ({
  prisma: {
    approvalQueue: { findMany: vi.fn().mockResolvedValue([]) },
    creative:      { findMany: vi.fn().mockResolvedValue([]) },
    influencer:    { findMany: vi.fn().mockResolvedValue([]) },
    post:          { findMany: vi.fn().mockResolvedValue([]) },
    attribution:   { findMany: vi.fn().mockResolvedValue([]) },
  },
  safeQuery: vi.fn().mockImplementation(
    (fn: () => Promise<unknown>) => fn(),
  ),
}));

vi.mock("@/lib/auth", () => ({
  requireSession: vi.fn(),
  requireRole:    vi.fn(),
  getCurrentUser: vi.fn(),
}));

import { GET as getApprovals }   from "@/app/api/approvals/route";
import { GET as getCreatives }   from "@/app/api/creatives/route";
import { GET as getInfluencers } from "@/app/api/influencers/route";
import { GET as getPosts }       from "@/app/api/posts/route";
import { GET as getAttribution } from "@/app/api/attribution/route";
import * as auth from "@/lib/auth";

const MOCK_USER = { email: "owner@test.com", role: "owner" as const, orgId: null };

describe("GET endpoints reject unauthenticated requests", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  type Handler = (req: Request) => Promise<Response>;

  const endpoints: { label: string; fn: Handler }[] = [
    { label: "/api/approvals",   fn: getApprovals },
    { label: "/api/creatives",   fn: getCreatives },
    { label: "/api/influencers", fn: getInfluencers },
    { label: "/api/posts",       fn: getPosts as Handler },
    { label: "/api/attribution", fn: getAttribution },
  ];

  for (const { label, fn } of endpoints) {
    it(`GET ${label} returns 401 without a session`, async () => {
      vi.mocked(auth.requireSession).mockImplementation(() =>
        Promise.resolve(
          new Response(JSON.stringify({ error: "authentication required" }), { status: 401 }),
        ),
      );
      const res = await fn(new Request(`http://localhost${label}`));
      expect(res.status).toBe(401);
    });

    it(`GET ${label} returns 200 with a valid session`, async () => {
      vi.mocked(auth.requireSession).mockResolvedValue(MOCK_USER);
      const res = await fn(new Request(`http://localhost${label}`));
      expect(res.status).toBe(200);
    });
  }
});
