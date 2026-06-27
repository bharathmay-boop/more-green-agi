"use client";
import { useState, useEffect } from "react";
import { Badge, toneFor } from "../_components/ui";
import { Actions } from "./Actions";

type Item = {
  id: number;
  actionType: string;
  entityRef: string | null;
  payloadJson: string | null;
  expectedImpactJson: string | null;
  requestedAt: Date | string;
  status: string;
};

function formatImpact(payload: string | null, impact: string | null): string {
  try {
    if (impact) {
      const p = JSON.parse(impact);
      if (p.revenue_inr && p.spend_inr) return `+₹${p.revenue_inr} rev / ₹${p.spend_inr} spend`;
    }
    if (payload) {
      const p = JSON.parse(payload);
      if (p.current_inr != null && p.proposed_inr != null) return `₹${p.current_inr} → ₹${p.proposed_inr}`;
      if (p.current_price != null && p.proposed_price != null) return `₹${p.current_price} → ₹${p.proposed_price}`;
    }
  } catch { /* noop */ }
  return "";
}

function prettyPayload(json: string | null): string {
  try { return JSON.stringify(JSON.parse(json ?? ""), null, 2); } catch { return json ?? ""; }
}

function relativeTime(date: Date | string): string {
  const ms = Math.max(0, Date.now() - new Date(date).getTime());
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor(ms / 60_000);
  if (h >= 24) return `${Math.floor(h / 24)}d ago`;
  if (h >= 1) return `${h}h ago`;
  return `${m}m ago`;
}

function absoluteTime(date: Date | string): string {
  return new Date(date).toLocaleDateString("en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function TimeAgo({ date }: { date: Date | string }) {
  const [label, setLabel] = useState(() => absoluteTime(date));
  useEffect(() => {
    setLabel(relativeTime(date));
    const id = setInterval(() => setLabel(relativeTime(date)), 60_000);
    return () => clearInterval(id);
  }, [date]);
  return <>{label}</>;
}

export function ApprovalCard({ item }: { item: Item }) {
  const [open, setOpen] = useState(false);
  const impact = formatImpact(item.payloadJson, item.expectedImpactJson);

  return (
    <div style={{ borderBottom: "1px solid var(--mg-border)" }}>
      <div
        role="button"
        tabIndex={0}
        style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", cursor: "pointer" }}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setOpen((o) => !o)}
        aria-expanded={open}
      >
        <div style={{ fontSize: 13, fontWeight: 600, minWidth: 160, color: "var(--mg-text)" }}>{item.actionType}</div>
        <div style={{ fontSize: 13, color: "var(--mg-muted)", flex: 1 }}>{item.entityRef}</div>
        <div style={{ fontSize: 13, color: "var(--mg-text)", minWidth: 140 }}>{impact}</div>
        <Badge tone={toneFor(item.status)}>{item.status}</Badge>
        <div style={{ fontSize: 11, color: "var(--mg-muted)", minWidth: 60, textAlign: "right" }}>
          <TimeAgo date={item.requestedAt} />
        </div>
        <div style={{ fontSize: 16, color: "var(--mg-muted)", userSelect: "none" }}>{open ? "▾" : "▸"}</div>
      </div>

      {open && (
        <div style={{ padding: "0 16px 16px", borderTop: "1px solid var(--mg-border)", background: "var(--mg-bg)" }}>
          {item.payloadJson && (
            <pre style={{ fontSize: 12, color: "var(--mg-muted)", margin: "12px 0", whiteSpace: "pre-wrap", overflowWrap: "break-word" }}>
              {prettyPayload(item.payloadJson)}
            </pre>
          )}
          <div style={{ marginTop: 8 }}>
            <Actions id={item.id} status={item.status} />
          </div>
        </div>
      )}
    </div>
  );
}
