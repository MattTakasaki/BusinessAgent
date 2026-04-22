// ============================================================
// Login Page — ai-agent-frontend/app/page.tsx
// Supabase email/password auth. Stores JWT in localStorage.
// On success redirects to /chat.
// ============================================================

"use client";

import { useState } from "react";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function LoginPage() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [mode, setMode]         = useState<"login" | "signup">("login");

  const handleSubmit = async () => {
    if (!email || !password) return;
    setLoading(true);
    setError("");

    try {
      const { data, error: authError } = mode === "login"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });

      if (authError) {
        setError(authError.message);
        return;
      }

      if (data.session) {
        localStorage.setItem("access_token", data.session.access_token);
        window.location.href = "/chat";
      } else if (mode === "signup") {
        setError("Check your email to confirm your account, then log in.");
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSubmit();
  };

  const inputStyle = {
    width: "100%", padding: "12px 14px",
    background: "#0d1117", border: "1px solid #1f2937",
    borderRadius: "8px", color: "#e5e7eb",
    fontSize: "14px", fontFamily: "inherit",
    outline: "none", boxSizing: "border-box" as const,
    transition: "border-color 0.15s ease",
  };

  return (
    <>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #060a0f; }
        input:focus { border-color: #2563eb !important; }
      `}</style>

      <div style={{
        minHeight: "100vh", background: "#060a0f",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "'DM Sans', system-ui, sans-serif",
        padding: "24px",
      }}>

        {/* Background grid */}
        <div style={{
          position: "fixed", inset: 0, zIndex: 0,
          backgroundImage: "linear-gradient(#0f172a 1px, transparent 1px), linear-gradient(90deg, #0f172a 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          opacity: 0.4,
        }} />

        <div style={{
          position: "relative", zIndex: 1,
          width: "100%", maxWidth: "380px",
        }}>

          {/* Logo */}
          <div style={{ textAlign: "center", marginBottom: "32px" }}>
            <div style={{
              width: "52px", height: "52px", borderRadius: "14px",
              background: "linear-gradient(135deg, #1d4ed8, #7c3aed)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "24px", margin: "0 auto 16px",
              boxShadow: "0 0 40px rgba(37,99,235,0.3)",
            }}>
              ✦
            </div>
            <div style={{ fontSize: "22px", fontWeight: 700, color: "#f9fafb", letterSpacing: "-0.02em" }}>
              Business Agent
            </div>
            <div style={{ fontSize: "13px", color: "#4b5563", marginTop: "4px" }}>
              {mode === "login" ? "Sign in to your workspace" : "Create your account"}
            </div>
          </div>

          {/* Card */}
          <div style={{
            background: "#0d1117", border: "1px solid #1f2937",
            borderRadius: "16px", padding: "28px",
          }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{
                  display: "block", fontSize: "12px", color: "#6b7280",
                  marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.06em",
                }}>
                  Email
                </label>
                <input
                  type="email"
                  style={inputStyle}
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="you@company.com"
                  autoComplete="email"
                />
              </div>
              <div>
                <label style={{
                  display: "block", fontSize: "12px", color: "#6b7280",
                  marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.06em",
                }}>
                  Password
                </label>
                <input
                  type="password"
                  style={inputStyle}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="••••••••"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                />
              </div>

              {error && (
                <div style={{
                  padding: "10px 12px", background: "rgba(239,68,68,0.08)",
                  border: "1px solid rgba(239,68,68,0.2)", borderRadius: "6px",
                  color: "#f87171", fontSize: "13px",
                }}>
                  {error}
                </div>
              )}

              <button
                onClick={handleSubmit}
                disabled={loading || !email || !password}
                style={{
                  width: "100%", padding: "12px",
                  background: loading || !email || !password ? "#1f2937" : "#2563eb",
                  color: loading || !email || !password ? "#4b5563" : "#fff",
                  border: "none", borderRadius: "8px",
                  fontSize: "14px", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
                  transition: "all 0.15s ease", marginTop: "4px",
                }}
              >
                {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
              </button>
            </div>
          </div>

          {/* Toggle mode */}
          <div style={{ textAlign: "center", marginTop: "20px", fontSize: "13px", color: "#4b5563" }}>
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            <button
              onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}
              style={{
                background: "none", border: "none", color: "#3b82f6",
                cursor: "pointer", fontSize: "13px", padding: 0,
              }}
            >
              {mode === "login" ? "Sign up" : "Sign in"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
