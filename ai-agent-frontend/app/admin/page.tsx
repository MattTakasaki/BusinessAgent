// ============================================================
// Admin Dashboard — ai-agent-frontend/app/admin/page.tsx
// Per-tenant agent configuration panel.
// Aesthetic: Dark industrial utility — like a mission control
// for AI agents. Sharp, dense, confident.
// ============================================================

"use client";

import { useState, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type AgentConfig = {
  agent_name: string;
  agent_tone: string;
  business_context: string;
  custom_instructions: string;
  enabled_tools: string[];
  branding: { primaryColor: string; logoUrl: string | null };
};

type UsageData = {
  plan: string;
  billing_period: string;
  claude_calls: { used: number; limit: number; remaining: number };
  tool_calls: { used: number; limit: number; remaining: number };
};

const ALL_TOOLS = [
  { id: "gmail_read",         label: "Gmail — Read",             group: "Google" },
  { id: "gmail_send",         label: "Gmail — Send",             group: "Google" },
  { id: "gcal_read",          label: "Calendar — Read",          group: "Google" },
  { id: "gcal_create",        label: "Calendar — Create Events", group: "Google" },
  { id: "sheets_read",        label: "Sheets — Read",            group: "Google" },
  { id: "sheets_write",       label: "Sheets — Write",           group: "Google" },
  { id: "outlook_read",       label: "Outlook — Read",           group: "Microsoft" },
  { id: "outlook_send",       label: "Outlook — Send",           group: "Microsoft" },
  { id: "outlook_cal_read",   label: "Calendar — Read",          group: "Microsoft" },
  { id: "outlook_cal_create", label: "Calendar — Create Events", group: "Microsoft" },
  { id: "excel_read",         label: "Excel — Read",             group: "Microsoft" },
  { id: "excel_write",        label: "Excel — Write",            group: "Microsoft" },
];

const DEFAULT_CONFIG: AgentConfig = {
  agent_name: "Assistant",
  agent_tone: "professional",
  business_context: "",
  custom_instructions: "",
  enabled_tools: ["gmail_read", "gcal_read"],
  branding: { primaryColor: "#2563eb", logoUrl: null },
};

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number }) {
  const pct = Math.min(100, Math.round((used / limit) * 100));
  const color = pct > 90 ? "#ef4444" : pct > 70 ? "#f59e0b" : "#22c55e";
  return (
    <div style={{ marginBottom: "12px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
        <span style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em", color: "#6b7280" }}>{label}</span>
        <span style={{ fontSize: "11px", fontFamily: "monospace", color: "#9ca3af" }}>{used.toLocaleString()} / {limit.toLocaleString()}</span>
      </div>
      <div style={{ height: "4px", background: "#1f2937", borderRadius: "2px" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: "2px", transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

function ToolToggle({ tool, enabled, onToggle }: { tool: typeof ALL_TOOLS[0]; enabled: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      style={{
        display: "flex", alignItems: "center", gap: "8px",
        padding: "8px 12px", borderRadius: "6px", border: "none", cursor: "pointer",
        background: enabled ? "rgba(37,99,235,0.15)" : "#111827",
        color: enabled ? "#93c5fd" : "#4b5563",
        fontSize: "12px", fontFamily: "monospace",
        transition: "all 0.15s ease",
        outline: enabled ? "1px solid rgba(37,99,235,0.4)" : "1px solid #1f2937",
      }}
    >
      <span style={{
        width: "6px", height: "6px", borderRadius: "50%",
        background: enabled ? "#3b82f6" : "#374151",
        flexShrink: 0,
      }} />
      {tool.label}
    </button>
  );
}

export default function AdminDashboard() {
  const [config, setConfig]   = useState<AgentConfig>(DEFAULT_CONFIG);
  const [usage, setUsage]     = useState<UsageData | null>(null);
  const [saving, setSaving]   = useState(false);
  const [saved, setSaved]     = useState(false);
  const [activeTab, setActiveTab] = useState<"identity" | "tools" | "usage">("identity");
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  useEffect(() => {
    if (!token) return;
    // Load existing config
    fetch(`${API_URL}/admin/config`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setConfig(data); })
      .catch(() => {});

    // Load usage
    fetch(`${API_URL}/usage/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setUsage(data); })
      .catch(() => {});
  }, [token]);

  const toggleTool = (toolId: string) => {
    setConfig(prev => ({
      ...prev,
      enabled_tools: prev.enabled_tools.includes(toolId)
        ? prev.enabled_tools.filter(t => t !== toolId)
        : [...prev.enabled_tools, toolId],
    }));
  };

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    try {
      await fetch(`${API_URL}/admin/config`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {}
    setSaving(false);
  };

  const googleTools    = ALL_TOOLS.filter(t => t.group === "Google");
  const microsoftTools = ALL_TOOLS.filter(t => t.group === "Microsoft");

  const inputStyle = {
    width: "100%", padding: "10px 12px",
    background: "#0d1117", border: "1px solid #1f2937",
    borderRadius: "6px", color: "#e5e7eb",
    fontSize: "13px", fontFamily: "monospace",
    outline: "none", boxSizing: "border-box" as const,
    resize: "vertical" as const,
  };

  const labelStyle = {
    display: "block", fontSize: "11px",
    textTransform: "uppercase" as const, letterSpacing: "0.08em",
    color: "#6b7280", marginBottom: "6px",
  };

  const tabStyle = (active: boolean) => ({
    padding: "8px 16px", fontSize: "12px", fontFamily: "monospace",
    textTransform: "uppercase" as const, letterSpacing: "0.06em",
    border: "none", cursor: "pointer", borderRadius: "4px",
    background: active ? "#1f2937" : "transparent",
    color: active ? "#e5e7eb" : "#4b5563",
    transition: "all 0.15s ease",
  });

  return (
    <div style={{
      minHeight: "100vh", background: "#060a0f",
      fontFamily: "'DM Mono', 'Courier New', monospace",
      color: "#e5e7eb",
    }}>
      {/* Header */}
      <div style={{
        borderBottom: "1px solid #0f172a",
        padding: "20px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div>
          <div style={{ fontSize: "11px", color: "#4b5563", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "2px" }}>
            Agent Control Panel
          </div>
          <div style={{ fontSize: "20px", fontWeight: 600, color: "#f9fafb", letterSpacing: "-0.02em" }}>
            {config.agent_name}
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: "10px 24px", borderRadius: "6px", border: "none",
            cursor: saving ? "not-allowed" : "pointer",
            background: saved ? "#166534" : "#2563eb",
            color: "#fff", fontSize: "12px", fontFamily: "monospace",
            textTransform: "uppercase", letterSpacing: "0.06em",
            transition: "all 0.2s ease",
            opacity: saving ? 0.7 : 1,
          }}
        >
          {saved ? "✓ Saved" : saving ? "Saving..." : "Save Config"}
        </button>
      </div>

      <div style={{ maxWidth: "860px", margin: "0 auto", padding: "32px" }}>

        {/* Tabs */}
        <div style={{ display: "flex", gap: "4px", marginBottom: "28px", background: "#0d1117", padding: "4px", borderRadius: "8px", width: "fit-content" }}>
          {(["identity", "tools", "usage"] as const).map(tab => (
            <button key={tab} style={tabStyle(activeTab === tab)} onClick={() => setActiveTab(tab)}>
              {tab}
            </button>
          ))}
        </div>

        {/* IDENTITY TAB */}
        {activeTab === "identity" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div>
                <label style={labelStyle}>Agent Name</label>
                <input
                  style={inputStyle}
                  value={config.agent_name}
                  onChange={e => setConfig(p => ({ ...p, agent_name: e.target.value }))}
                  placeholder="e.g. Acme Assistant"
                />
              </div>
              <div>
                <label style={labelStyle}>Tone</label>
                <select
                  style={{ ...inputStyle, cursor: "pointer" }}
                  value={config.agent_tone}
                  onChange={e => setConfig(p => ({ ...p, agent_tone: e.target.value }))}
                >
                  <option value="professional">Professional</option>
                  <option value="formal">Formal</option>
                  <option value="casual">Casual</option>
                  <option value="friendly">Friendly</option>
                </select>
              </div>
            </div>

            <div>
              <label style={labelStyle}>Business Context</label>
              <textarea
                style={{ ...inputStyle, minHeight: "100px" }}
                value={config.business_context}
                onChange={e => setConfig(p => ({ ...p, business_context: e.target.value }))}
                placeholder="Describe this business — industry, size, key workflows, important contacts..."
              />
            </div>

            <div>
              <label style={labelStyle}>Custom Instructions</label>
              <textarea
                style={{ ...inputStyle, minHeight: "100px" }}
                value={config.custom_instructions}
                onChange={e => setConfig(p => ({ ...p, custom_instructions: e.target.value }))}
                placeholder="e.g. Never book meetings on Fridays after 3pm. Always CC the manager on external emails..."
              />
            </div>

            <div>
              <label style={labelStyle}>Brand Color</label>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input
                  type="color"
                  value={config.branding.primaryColor}
                  onChange={e => setConfig(p => ({ ...p, branding: { ...p.branding, primaryColor: e.target.value } }))}
                  style={{ width: "40px", height: "40px", border: "none", background: "none", cursor: "pointer", borderRadius: "6px" }}
                />
                <input
                  style={{ ...inputStyle, width: "140px" }}
                  value={config.branding.primaryColor}
                  onChange={e => setConfig(p => ({ ...p, branding: { ...p.branding, primaryColor: e.target.value } }))}
                  placeholder="#2563eb"
                />
              </div>
            </div>
          </div>
        )}

        {/* TOOLS TAB */}
        {activeTab === "tools" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            {[{ label: "Google Workspace", tools: googleTools }, { label: "Microsoft 365", tools: microsoftTools }].map(group => (
              <div key={group.label}>
                <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.1em", color: "#4b5563", marginBottom: "12px" }}>
                  {group.label}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {group.tools.map(tool => (
                    <ToolToggle
                      key={tool.id}
                      tool={tool}
                      enabled={config.enabled_tools.includes(tool.id)}
                      onToggle={() => toggleTool(tool.id)}
                    />
                  ))}
                </div>
              </div>
            ))}
            <div style={{ padding: "12px 16px", background: "#0d1117", borderRadius: "6px", border: "1px solid #1f2937" }}>
              <div style={{ fontSize: "11px", color: "#4b5563", marginBottom: "4px" }}>ENABLED TOOLS</div>
              <div style={{ fontSize: "12px", fontFamily: "monospace", color: "#6b7280" }}>
                {config.enabled_tools.length === 0
                  ? "No tools enabled"
                  : config.enabled_tools.join(", ")}
              </div>
            </div>
          </div>
        )}

        {/* USAGE TAB */}
        {activeTab === "usage" && (
          <div>
            {usage ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <div style={{ display: "flex", gap: "12px" }}>
                  <div style={{ padding: "8px 16px", background: "#0d1117", border: "1px solid #1f2937", borderRadius: "6px", fontSize: "12px" }}>
                    <span style={{ color: "#4b5563" }}>Plan: </span>
                    <span style={{ color: "#93c5fd", textTransform: "uppercase" }}>{usage.plan}</span>
                  </div>
                  <div style={{ padding: "8px 16px", background: "#0d1117", border: "1px solid #1f2937", borderRadius: "6px", fontSize: "12px" }}>
                    <span style={{ color: "#4b5563" }}>Period: </span>
                    <span style={{ color: "#9ca3af" }}>{usage.billing_period}</span>
                  </div>
                </div>
                <div style={{ padding: "20px", background: "#0d1117", border: "1px solid #1f2937", borderRadius: "8px" }}>
                  <UsageBar label="Claude Calls" used={usage.claude_calls.used} limit={usage.claude_calls.limit} />
                  <UsageBar label="Tool Calls"   used={usage.tool_calls.used}   limit={usage.tool_calls.limit} />
                </div>
              </div>
            ) : (
              <div style={{ color: "#4b5563", fontSize: "13px" }}>Loading usage data...</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
