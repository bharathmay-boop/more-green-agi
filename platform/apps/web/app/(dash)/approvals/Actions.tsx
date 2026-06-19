"use client";
// Client-side approve/reject/apply buttons for the Approvals screen (E3-T4).
import { useState } from "react";
import { useRouter } from "next/navigation";

const btn = (bg: string): React.CSSProperties => ({
  background: bg, color: "#fff", border: 0, borderRadius: 6, padding: "6px 12px",
  fontSize: 13, fontWeight: 600, cursor: "pointer",
});

export function Actions({ id, status }: { id: number; status: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function act(action: "approve" | "reject" | "apply") {
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch(`/api/approvals/${id}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (!res.ok) setMsg(data.error || "failed");
      else { setMsg(action === "apply" ? "queued" : action + "d"); router.refresh(); }
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      {status === "pending" && (
        <>
          <button style={btn("#08a045")} disabled={busy} onClick={() => act("approve")}>Approve</button>
          <button style={btn("#b3261e")} disabled={busy} onClick={() => act("reject")}>Reject</button>
        </>
      )}
      {status === "approved" && (
        <button style={btn("#1a56c4")} disabled={busy} onClick={() => act("apply")}>Apply</button>
      )}
      {msg && <span style={{ fontSize: 12, color: "var(--mg-muted)" }}>{msg}</span>}
    </div>
  );
}
