/**
 * Shared presentational helpers for the dashboard screens. Inline styles match
 * the brand tokens in app/globals.css (house pattern — no CSS framework).
 */
import type { ReactNode } from "react";

export function PageHeader({ title, subtitle, actions }: {
  title: string; subtitle?: string; actions?: ReactNode;
}) {
  return (
    <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20, gap: 16 }}>
      <div>
        <h1 style={{ margin: "0 0 4px", fontSize: 24 }}>{title}</h1>
        {subtitle && <p style={{ color: "var(--mg-muted)", margin: 0, maxWidth: 680, fontSize: 14 }}>{subtitle}</p>}
      </div>
      {actions && <div style={{ flexShrink: 0 }}>{actions}</div>}
    </header>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ border: "1px solid var(--mg-border)", borderRadius: 8, background: "var(--mg-surface)", padding: 16, ...style }}>
      {children}
    </div>
  );
}

const BADGE_TONES: Record<string, { bg: string; fg: string }> = {
  green: { bg: "#e6f6ec", fg: "#067a35" },
  amber: { bg: "#fdf3e0", fg: "#9a6a00" },
  red: { bg: "#fbe9e9", fg: "#b3261e" },
  blue: { bg: "#e8f0fe", fg: "#1a56c4" },
  gray: { bg: "#eef1ef", fg: "#6b746f" },
};

/** Map a free-form status string to a tone. */
export function toneFor(status?: string | null): keyof typeof BADGE_TONES {
  const s = (status || "").toLowerCase();
  if (["approved", "done", "active", "selected", "ready", "published", "posted"].some((k) => s.includes(k))) return "green";
  if (["pending", "in_progress", "generating", "draft", "scheduled", "queued", "discovered"].some((k) => s.includes(k))) return "amber";
  if (["rejected", "failed", "blocked", "dead", "error", "paused", "expired"].some((k) => s.includes(k))) return "red";
  return "gray";
}

export function Badge({ children, tone }: { children: ReactNode; tone?: keyof typeof BADGE_TONES }) {
  const t = BADGE_TONES[tone || "gray"];
  return (
    <span style={{ background: t.bg, color: t.fg, padding: "2px 8px", borderRadius: 100, fontSize: 12, fontWeight: 600, whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div style={{ border: "1px dashed var(--mg-border)", borderRadius: 8, padding: "32px 24px", background: "var(--mg-surface)", color: "var(--mg-muted)", fontSize: 14, textAlign: "center" }}>
      {children}
    </div>
  );
}

export const td: React.CSSProperties = { padding: "10px 12px", borderBottom: "1px solid var(--mg-border)", fontSize: 14, textAlign: "left", verticalAlign: "top" };
export const th: React.CSSProperties = { ...td, color: "var(--mg-muted)", fontWeight: 600, fontSize: 12, textTransform: "uppercase", letterSpacing: 0.4 };

export function Stat({ label, value, tone, secondary }: {
  label: string; value: string | number; tone?: keyof typeof BADGE_TONES; secondary?: string;
}) {
  const t = tone ? BADGE_TONES[tone] : BADGE_TONES.gray;
  return (
    <div>
      <p style={{ fontSize: 14, color: "var(--mg-muted)", margin: "0 0 4px" }}>{label}</p>
      <p style={{ fontSize: 22, fontWeight: 600, margin: "0 0 8px" }}>{value}</p>
      {secondary && <p style={{ fontSize: 12, color: t.fg, background: t.bg, padding: "2px 8px", borderRadius: 100, width: "fit-content" }}>{secondary}</p>}
    </div>
  );
}

export function SectionCard({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <Card>
      <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 16px" }}>{title}</h2>
      {children}
    </Card>
  );
}

export function ImageThumb({ src, alt, size = 64 }: { src: string; alt: string; size?: number }) {
  return (
    <img
      src={src}
      alt={alt}
      style={{ width: size, height: size, borderRadius: 6, objectFit: "cover" }}
    />
  );
}
