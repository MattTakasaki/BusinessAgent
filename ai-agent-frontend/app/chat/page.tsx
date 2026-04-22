// ============================================================
// Client Portal — ai-agent-frontend/app/chat/page.tsx
// The main chat interface for end users.
// Aesthetic: Dark, focused, terminal-inspired but warm.
// Clean message bubbles, real-time streaming, tool use indicators.
// ============================================================

"use client";

import { useState, useEffect, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type MessageRole = "user" | "assistant" | "tool_use" | "tool_error" | "error";

type Message = {
  id: string;
  role: MessageRole;
  content: string;
  tool?: string;
  timestamp: Date;
};

function ToolIndicator({ tool, error }: { tool: string; error?: boolean }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: "6px",
      padding: "4px 10px", borderRadius: "4px",
      background: error ? "rgba(239,68,68,0.1)" : "rgba(37,99,235,0.1)",
      border: `1px solid ${error ? "rgba(239,68,68,0.2)" : "rgba(37,99,235,0.2)"}`,
      fontSize: "11px", fontFamily: "monospace",
      color: error ? "#f87171" : "#93c5fd",
      margin: "4px 0",
    }}>
      <span style={{
        width: "5px", height: "5px", borderRadius: "50%",
        background: error ? "#ef4444" : "#3b82f6",
        animation: error ? "none" : "pulse 1.5s infinite",
      }} />
      {error ? `✗ ${tool} failed` : `⟳ ${tool}`}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  if (message.role === "tool_use") {
    return (
      <div style={{ display: "flex", justifyContent: "center", margin: "4px 0" }}>
        <ToolIndicator tool={message.tool || ""} />
      </div>
    );
  }

  if (message.role === "tool_error") {
    return (
      <div style={{ display: "flex", justifyContent: "center", margin: "4px 0" }}>
        <ToolIndicator tool={message.tool || ""} error />
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div style={{
        margin: "8px 0", padding: "10px 14px",
        background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
        borderRadius: "8px", color: "#f87171", fontSize: "13px",
      }}>
        {message.content}
      </div>
    );
  }

  return (
    <div style={{
      display: "flex",
      justifyContent: isUser ? "flex-end" : "flex-start",
      margin: "6px 0",
    }}>
      {!isUser && (
        <div style={{
          width: "28px", height: "28px", borderRadius: "6px",
          background: "linear-gradient(135deg, #1d4ed8, #7c3aed)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "12px", marginRight: "8px", flexShrink: 0, marginTop: "2px",
        }}>
          ✦
        </div>
      )}
      <div style={{
        maxWidth: "72%",
        padding: "10px 14px",
        borderRadius: isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
        background: isUser ? "#1d4ed8" : "#111827",
        color: isUser ? "#eff6ff" : "#e5e7eb",
        fontSize: "14px", lineHeight: "1.6",
        border: isUser ? "none" : "1px solid #1f2937",
        whiteSpace: "pre-wrap", wordBreak: "break-word",
      }}>
        {message.content}
        <div style={{
          fontSize: "10px", marginTop: "4px", opacity: 0.4,
          textAlign: isUser ? "right" : "left",
          fontFamily: "monospace",
        }}>
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", margin: "6px 0" }}>
      <div style={{
        width: "28px", height: "28px", borderRadius: "6px",
        background: "linear-gradient(135deg, #1d4ed8, #7c3aed)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "12px", flexShrink: 0,
      }}>
        ✦
      </div>
      <div style={{
        padding: "10px 14px", borderRadius: "12px 12px 12px 2px",
        background: "#111827", border: "1px solid #1f2937",
        display: "flex", gap: "4px", alignItems: "center",
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: "6px", height: "6px", borderRadius: "50%",
            background: "#4b5563",
            animation: `bounce 1.2s ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages]     = useState<Message[]>([]);
  const [input, setInput]           = useState("");
  const [streaming, setStreaming]   = useState(false);
  const [sessionId]                 = useState(() => crypto.randomUUID());
  const [agentName, setAgentName]   = useState("Assistant");
  const bottomRef                   = useRef<HTMLDivElement>(null);
  const inputRef                    = useRef<HTMLTextAreaElement>(null);
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  // Load agent name from config
  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/admin/config`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.agent_name) setAgentName(data.agent_name); })
      .catch(() => {});
  }, [token]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (msg: Omit<Message, "id" | "timestamp">) => {
    const full: Message = { ...msg, id: crypto.randomUUID(), timestamp: new Date() };
    setMessages(prev => [...prev, full]);
    return full.id;
  };

  const appendToLastAssistant = (chunk: string) => {
    setMessages(prev => {
      const copy = [...prev];
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].role === "assistant") {
          copy[i] = { ...copy[i], content: copy[i].content + chunk };
          return copy;
        }
      }
      // No assistant message yet — create one
      return [...copy, { id: crypto.randomUUID(), role: "assistant", content: chunk, timestamp: new Date() }];
    });
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || streaming || !token) return;

    setInput("");
    setStreaming(true);

    addMessage({ role: "user", content: text });

    try {
      const response = await fetch(`${API_URL}/chat/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      if (!response.ok) {
        addMessage({ role: "error", content: "Failed to reach the agent. Please try again." });
        setStreaming(false);
        return;
      }

      const reader  = response.body!.getReader();
      const decoder = new TextDecoder();
      let   buffer  = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));

            if (event.type === "text") {
              appendToLastAssistant(event.content);
            } else if (event.type === "tool_use") {
              addMessage({ role: "tool_use", content: "", tool: event.tool });
            } else if (event.type === "tool_error") {
              addMessage({ role: "tool_error", content: "", tool: event.tool });
            } else if (event.type === "error") {
              addMessage({ role: "error", content: event.content });
            } else if (event.type === "done") {
              setStreaming(false);
            }
          } catch {}
        }
      }
    } catch (err) {
      addMessage({ role: "error", content: "Connection error. Is the backend running?" });
    }

    setStreaming(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #060a0f; }
        textarea:focus { outline: none; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1f2937; border-radius: 2px; }
      `}</style>

      <div style={{
        display: "flex", flexDirection: "column",
        height: "100vh", background: "#060a0f",
        fontFamily: "'DM Sans', system-ui, sans-serif",
        color: "#e5e7eb",
      }}>

        {/* Header */}
        <div style={{
          padding: "16px 24px",
          borderBottom: "1px solid #0f172a",
          display: "flex", alignItems: "center", gap: "12px",
          background: "rgba(6,10,15,0.95)",
          backdropFilter: "blur(8px)",
          position: "sticky", top: 0, zIndex: 10,
        }}>
          <div style={{
            width: "36px", height: "36px", borderRadius: "8px",
            background: "linear-gradient(135deg, #1d4ed8, #7c3aed)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "16px",
          }}>
            ✦
          </div>
          <div>
            <div style={{ fontSize: "15px", fontWeight: 600, letterSpacing: "-0.01em" }}>{agentName}</div>
            <div style={{ fontSize: "11px", color: "#22c55e", display: "flex", alignItems: "center", gap: "4px" }}>
              <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: "#22c55e", display: "inline-block" }} />
              Online
            </div>
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: "auto",
          padding: "24px",
          display: "flex", flexDirection: "column",
        }}>
          {messages.length === 0 && (
            <div style={{
              flex: 1, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              color: "#374151", textAlign: "center", gap: "12px",
            }}>
              <div style={{ fontSize: "40px" }}>✦</div>
              <div style={{ fontSize: "16px", fontWeight: 500, color: "#4b5563" }}>
                How can I help you today?
              </div>
              <div style={{ fontSize: "13px", color: "#374151", maxWidth: "340px", lineHeight: "1.6" }}>
                I can read your email, check your calendar, update spreadsheets, and more.
              </div>
            </div>
          )}

          {messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {streaming && messages[messages.length - 1]?.role !== "assistant" && (
            <TypingIndicator />
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{
          padding: "16px 24px 24px",
          borderTop: "1px solid #0f172a",
          background: "rgba(6,10,15,0.95)",
          backdropFilter: "blur(8px)",
        }}>
          <div style={{
            display: "flex", gap: "10px", alignItems: "flex-end",
            background: "#0d1117", border: "1px solid #1f2937",
            borderRadius: "12px", padding: "10px 12px",
            transition: "border-color 0.15s ease",
          }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message your assistant... (Enter to send, Shift+Enter for new line)"
              disabled={streaming}
              rows={1}
              style={{
                flex: 1, background: "transparent", border: "none",
                color: "#e5e7eb", fontSize: "14px", lineHeight: "1.5",
                resize: "none", fontFamily: "inherit",
                maxHeight: "120px", overflowY: "auto",
                opacity: streaming ? 0.6 : 1,
              }}
            />
            <button
              onClick={sendMessage}
              disabled={streaming || !input.trim()}
              style={{
                width: "34px", height: "34px", borderRadius: "8px",
                border: "none", cursor: streaming || !input.trim() ? "not-allowed" : "pointer",
                background: streaming || !input.trim() ? "#1f2937" : "#2563eb",
                color: streaming || !input.trim() ? "#4b5563" : "#fff",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "16px", flexShrink: 0,
                transition: "all 0.15s ease",
              }}
            >
              ↑
            </button>
          </div>
          <div style={{ fontSize: "11px", color: "#1f2937", textAlign: "center", marginTop: "8px", fontFamily: "monospace" }}>
            Actions taken by the agent are logged in your audit trail.
          </div>
        </div>
      </div>
    </>
  );
}
