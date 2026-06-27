"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Badge, toneFor } from "../_components/ui";

type Creative = {
  id: number;
  kind: string;
  variantIndex: number;
  cloudinaryUrl: string | null;
  status: string;
  score: number | null;
  costUsd: number | null;
};

const btn = (bg: string, disabled?: boolean): React.CSSProperties => ({
  background: disabled ? "var(--mg-border)" : bg,
  color: disabled ? "var(--mg-muted)" : "#fff",
  border: 0, borderRadius: 6, padding: "5px 10px", fontSize: 12, fontWeight: 600,
  cursor: disabled ? "default" : "pointer",
});

export function CreativeCard({ creative }: { creative: Creative }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [localStatus, setLocalStatus] = useState(creative.status);

  async function setStatus(status: "selected" | "rejected" | "ready") {
    setBusy(true);
    try {
      const res = await fetch(`/api/creatives/${creative.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (res.ok) { setLocalStatus(status); router.refresh(); }
    } finally {
      setBusy(false);
    }
  }

  const isSelected = localStatus === "selected";
  const isRejected = localStatus === "rejected";
  const isSettled = isSelected || isRejected;

  return (
    <div style={{ border: `2px solid ${isSelected ? "var(--mg-green)" : isRejected ? "#b3261e" : "var(--mg-border)"}`, borderRadius: 10, overflow: "hidden", background: "var(--mg-surface)", display: "flex", flexDirection: "column" }}>
      <div style={{ width: "100%", aspectRatio: "1/1", background: "var(--mg-border)", overflow: "hidden" }}>
        {creative.cloudinaryUrl
          ? <img src={creative.cloudinaryUrl} alt={`variant ${creative.variantIndex}`} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          : <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--mg-muted)", fontSize: 12 }}>No image</div>
        }
      </div>

      <div style={{ padding: 10, display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Badge tone={toneFor(creative.kind)}>{creative.kind}</Badge>
          <Badge tone={toneFor(localStatus)}>{localStatus}</Badge>
          <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--mg-muted)" }}>v{creative.variantIndex}</span>
        </div>

        {(creative.score != null || creative.costUsd != null) && (
          <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--mg-muted)" }}>
            {creative.score != null && <span>Score: {creative.score.toFixed(2)}</span>}
            {creative.costUsd != null && <span>Cost: ${creative.costUsd.toFixed(3)}</span>}
          </div>
        )}

        <div style={{ display: "flex", gap: 6, marginTop: 2 }}>
          <button style={btn("#08a045", busy || isSelected)} disabled={busy || isSelected} onClick={() => setStatus("selected")}>
            {isSelected ? "✓ Selected" : "Select"}
          </button>
          <button style={btn("#b3261e", busy || isRejected)} disabled={busy || isRejected} onClick={() => setStatus("rejected")}>
            {isRejected ? "✗ Rejected" : "Reject"}
          </button>
          {isSettled && (
            <button style={btn("#6b746f", busy)} disabled={busy} onClick={() => setStatus("ready")}>
              Reset
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
