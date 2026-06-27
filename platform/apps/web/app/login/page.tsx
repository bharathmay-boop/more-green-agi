"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        router.push("/");
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "Invalid credentials");
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--mg-bg)" }}>
      <div style={{ width: 360, padding: 40, background: "var(--mg-surface)", borderRadius: 12, border: "1px solid var(--mg-border)" }}>
        <div style={{ fontFamily: "Archivo, sans-serif", fontWeight: 600, fontSize: 22, color: "var(--mg-green)", marginBottom: 24 }}>
          More Green
        </div>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ padding: "10px 12px", borderRadius: 6, border: "1px solid var(--mg-border)", fontSize: 14, background: "var(--mg-bg)", color: "var(--mg-text)" }}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ padding: "10px 12px", borderRadius: 6, border: "1px solid var(--mg-border)", fontSize: 14, background: "var(--mg-bg)", color: "var(--mg-text)" }}
          />
          {error && <div style={{ color: "#e53e3e", fontSize: 13 }}>{error}</div>}
          <button
            type="submit"
            disabled={loading}
            style={{ padding: "10px 0", background: "var(--mg-green)", color: "#fff", border: "none", borderRadius: 6, fontWeight: 600, fontSize: 14, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
