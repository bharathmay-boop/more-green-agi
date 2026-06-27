import Link from "next/link";
import { prisma, safeQuery } from "@/lib/db";

const NAV: { href: string; label: string }[] = [
  { href: "/", label: "Home" },
  { href: "/calendar", label: "Calendar" },
  { href: "/creatives", label: "Creative Review" },
  { href: "/approvals", label: "Approvals" },
  { href: "/roas", label: "ROAS" },
  { href: "/influencers", label: "Influencers" },
  { href: "/build", label: "Build" },
  { href: "/audit", label: "Audit" },
];

export default async function DashLayout({ children }: { children: React.ReactNode }) {
  const pendingCount = await safeQuery(
    () => prisma.approvalQueue.count({ where: { status: { in: ["pending", "approved"] } } }),
    0,
  );

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside style={{ width: 220, flexShrink: 0, borderRight: "1px solid var(--mg-border)", background: "var(--mg-surface)", padding: "20px 12px" }}>
        <div style={{ fontFamily: "Archivo, sans-serif", fontWeight: 600, fontSize: 18, color: "var(--mg-green)", padding: "0 8px 16px" }}>
          More Green
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              style={{ padding: "8px 10px", borderRadius: 6, fontSize: 14, color: "var(--mg-text)", display: "flex", alignItems: "center", justifyContent: "space-between" }}
            >
              {item.label}
              {item.href === "/approvals" && pendingCount > 0 && (
                <span style={{ background: "#f3c06d", color: "#7a5200", fontSize: 11, fontWeight: 700, borderRadius: 100, minWidth: 18, height: 18, display: "flex", alignItems: "center", justifyContent: "center", padding: "0 5px" }}>
                  {pendingCount}
                </span>
              )}
            </Link>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1, maxWidth: "var(--mg-max-width)", width: "100%", padding: "28px 32px" }}>
        {children}
      </main>
    </div>
  );
}
