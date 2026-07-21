"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Layout } from "@/app/components/Layout";
import {
  Bot, Send, Loader2, CheckCircle, XCircle, Globe, HardDrive,
  RefreshCw, Sparkles, Download, Brain, MessageSquare, Plus, Trash2, ChevronLeft
} from "lucide-react";
import { getHeaders, apiUrl } from "@/app/api/api";
import useSWR from "swr";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Msg {
  id: number;
  role: "user" | "agent" | "tool" | "thinking";
  text: string;
  toolName?: string;
  toolParams?: string;
  toolStatus?: "pending" | "approved" | "refused";
  ts: number;
}

interface Conversation {
  id: number;
  title: string;
  last_message: string;
  updated_at: string;
}

interface Memory {
  id: number;
  name: string;
  description: string;
  type: string;
}

interface SystemHealth {
  hostname: string;
  cpu: number;
  ram: number;
  instances: number;
}

interface ActionItem {
  id: number;
  action_type: string;
  params: Record<string, unknown>;
  status: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const swrFetcher = async (url: string) => {
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) throw new Error(`SWR ${res.status}`);
  return res.json();
};

function formatMd(text: string): string {
  return text
    .replace(/```([\s\S]*?)```/g, '<pre class="log-block">$1</pre>')
    .replace(/`([^`]+)`/g, '<code class="mono">$1</code>')
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

let msgIdSeq = 0;
const nextId = () => ++msgIdSeq;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function AIPage() {
  /* ---------- state ---------- */
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [showMemory, setShowMemory] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const esRef = useRef<EventSource | null>(null);

  /* ---------- data fetching ---------- */
  const { data: conversations, mutate: mutateConvos } = useSWR<Conversation[]>(
    apiUrl("/api/v1/conversations"),
    swrFetcher,
    { refreshInterval: 10000 }
  );

  const { data: memories, mutate: mutateMemories } = useSWR<Memory[]>(
    apiUrl("/api/v1/memory/memories"),
    swrFetcher,
    { refreshInterval: 30000 }
  );

  /* ---------- system health ---------- */
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(apiUrl("/api/v1/system/health"), { headers: getHeaders() });
        if (res.ok) setSystemHealth(await res.json());
      } catch { /* ignore */ }
    };
    fetchHealth();
    const iv = setInterval(fetchHealth, 15000);
    return () => clearInterval(iv);
  }, []);

  /* ---------- auto scroll ---------- */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ---------- load conversation ---------- */
  const loadConversation = useCallback(async (id: number) => {
    setActiveConversationId(id);
    try {
      const res = await fetch(apiUrl(`/api/v1/conversations/${id}/messages`), { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setMessages(
          data.map((m: { role: string; content: string }) => ({
            id: nextId(),
            role: m.role === "assistant" ? "agent" : m.role === "tool" ? "tool" : "user",
            text: m.content,
            ts: Date.now(),
          }))
        );
      }
    } catch { /* ignore */ }
  }, []);

  /* ---------- delete memory ---------- */
  const deleteMemory = useCallback(async (id: number) => {
    await fetch(apiUrl(`/api/v1/memory/memories/${id}`), {
      method: "DELETE",
      headers: getHeaders(),
    });
    mutateMemories();
  }, [mutateMemories]);

  /* ---------- poll actions for approval ---------- */
  const pollActions = useCallback((jobId: string) => {
    const iv = setInterval(async () => {
      try {
        const res = await fetch(apiUrl(`/api/v1/agent/actions?job_id=${jobId}`), { headers: getHeaders() });
        if (!res.ok) return;
        const actions: ActionItem[] = await res.json();
        actions.forEach((a) => {
          if (a.status === "pending_approval") {
            setMessages((prev) => {
              if (prev.some((m) => m.id === a.id && m.role === "tool")) return prev;
              return [
                ...prev,
                {
                  id: a.id,
                  role: "tool",
                  text: "",
                  toolName: a.action_type,
                  toolParams: JSON.stringify(a.params, null, 2),
                  toolStatus: "pending",
                  ts: Date.now(),
                },
              ];
            });
          }
        });
      } catch { /* ignore */ }
    }, 2000);
    return () => clearInterval(iv);
  }, []);

  /* ---------- approve / refuse action ---------- */
  const handleActionResponse = useCallback(async (actionId: number, approve: boolean) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === actionId ? { ...m, toolStatus: approve ? "approved" : "refused" } : m
      )
    );
    try {
      await fetch(apiUrl(`/api/v1/agent/actions/${actionId}`), {
        method: "POST",
        headers: { ...getHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ status: approve ? "approved" : "refused" }),
      });
    } catch { /* ignore */ }
  }, []);

  /* ---------- send message (SSE) ---------- */
  const sendMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isRunning) return;

    setInput("");
    setIsRunning(true);

    const userMsg: Msg = { id: nextId(), role: "user", text: trimmed, ts: Date.now() };
    setMessages((prev) => [...prev, userMsg]);

    const thinkingMsg: Msg = { id: nextId(), role: "thinking", text: "", ts: Date.now() };
    setMessages((prev) => [...prev, thinkingMsg]);

    try {
      const runRes = await fetch(apiUrl("/api/v1/agent/run"), {
        method: "POST",
        headers: { ...getHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ goal: trimmed }),
      });
      const runData = await runRes.json();
      const jobId: string = runData.id ?? runData.job_id ?? "";

      /* remove thinking, start SSE */
      setMessages((prev) => prev.filter((m) => m.id !== thinkingMsg.id));

      const stopPoll = pollActions(jobId);

      const es = new EventSource(apiUrl(`/api/v1/agent/jobs/${jobId}/stream`), { withCredentials: true });
      esRef.current = es;

      es.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data);
          const eventType = payload.type ?? payload.event ?? "";

          if (eventType === "plan") {
            setMessages((prev) => [
              ...prev,
              { id: nextId(), role: "agent", text: `**Plan:** ${payload.text ?? payload.message ?? ""}`, ts: Date.now() },
            ]);
          } else if (eventType === "step") {
            setMessages((prev) => [
              ...prev,
              { id: nextId(), role: "agent", text: payload.text ?? payload.message ?? "", ts: Date.now() },
            ]);
          } else if (eventType === "done") {
            setMessages((prev) => [
              ...prev,
              { id: nextId(), role: "agent", text: payload.text ?? payload.result ?? "Done.", ts: Date.now() },
            ]);
            es.close();
            esRef.current = null;
            stopPoll();
            setIsRunning(false);
            mutateConvos();
          }
        } catch { /* non-JSON frame */ }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        stopPoll();
        setIsRunning(false);
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "agent", text: "⚠️ Connection lost. The agent may still be running.", ts: Date.now() },
        ]);
      };
    } catch {
      setMessages((prev) => prev.filter((m) => m.id !== thinkingMsg.id));
      setIsRunning(false);
    }
  }, [input, isRunning, pollActions, mutateConvos]);

  /* ---------- new chat ---------- */
  const newChat = useCallback(() => {
    setMessages([]);
    setActiveConversationId(null);
    setInput("");
  }, []);

  /* ---------- export conversation ---------- */
  const exportConversation = useCallback(() => {
    const lines = messages.map((m) => {
      if (m.role === "user") return `## User\n${m.text}`;
      if (m.role === "agent") return `## Agent\n${m.text}`;
      if (m.role === "tool") return `## Tool: ${m.toolName}\n\`\`\`\n${m.toolParams}\n\`\`\`\nStatus: ${m.toolStatus}`;
      return "";
    });
    const blob = new Blob([lines.join("\n\n")], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `conversation-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [messages]);

  /* ---------- quick actions ---------- */
  const quickActions = [
    { label: "Check servers", icon: Globe, goal: "Check the status of all running server instances" },
    { label: "Disk usage", icon: HardDrive, goal: "Analyze disk usage and report any partitions above 80%" },
    { label: "System update", icon: RefreshCw, goal: "Check for available system updates and summarize" },
    { label: "Deploy", icon: Sparkles, goal: "Show current deployment status and available actions" },
  ];

  /* ---------- key handler ---------- */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /* ================================================================ */
  /*  Render                                                           */
  /* ================================================================ */

  return (
    <Layout>
      <div style={{ display: "flex", height: "calc(100vh - 64px)", overflow: "hidden" }}>

        {/* ===== Conversation Sidebar ===== */}
        {showSidebar && (
          <aside
            className="anim-fade"
            style={{
              width: 280,
              minWidth: 280,
              borderRight: "1px solid var(--s2)",
              display: "flex",
              flexDirection: "column",
              background: "var(--s0)",
            }}
          >
            <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--s2)" }}>
              <button className="btn btn-primary" style={{ width: "100%", display: "flex", alignItems: "center", gap: 8, justifyContent: "center" }} onClick={newChat}>
                <Plus size={16} /> New Chat
              </button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
              {conversations?.map((c) => (
                <div
                  key={c.id}
                  onClick={() => loadConversation(c.id)}
                  style={{
                    padding: "10px 16px",
                    cursor: "pointer",
                    background: activeConversationId === c.id ? "var(--s2)" : "transparent",
                    borderLeft: activeConversationId === c.id ? "3px solid var(--accent)" : "3px solid transparent",
                    transition: "background 0.15s",
                  }}
                >
                  <div className="truncate" style={{ fontWeight: 600, fontSize: 13, color: "var(--t1)" }}>
                    {c.title || "Untitled"}
                  </div>
                  <div className="truncate" style={{ fontSize: 12, color: "var(--t3)", marginTop: 2 }}>
                    {c.last_message}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--t3)", marginTop: 4 }}>
                    {timeAgo(c.updated_at)}
                  </div>
                </div>
              ))}
              {(!conversations || conversations.length === 0) && (
                <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--t3)", fontSize: 13 }}>
                  No conversations yet
                </div>
              )}
            </div>
          </aside>
        )}

        {/* ===== Chat Area ===== */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>

          {/* Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderBottom: "1px solid var(--s2)",
              background: "var(--s0)",
            }}
          >
            <button className="btn btn-ghost btn-sm btn-icon" onClick={() => setShowSidebar(!showSidebar)} title="Toggle sidebar">
              {showSidebar ? <ChevronLeft size={18} /> : <MessageSquare size={18} />}
            </button>

            <Bot size={20} style={{ color: "var(--accent)" }} />
            <span style={{ fontWeight: 700, fontSize: 15, color: "var(--t1)" }}>Opsora Agent</span>

            {systemHealth && (
              <span
                className="tag tag-info"
                style={{ fontSize: 11, marginLeft: 8 }}
              >
                {systemHealth.hostname} · CPU {systemHealth.cpu}% · {systemHealth.instances} instances
              </span>
            )}

            <div style={{ flex: 1 }} />

            <button className="btn btn-ghost btn-sm btn-icon" onClick={() => setShowMemory(!showMemory)} title="Memories">
              <Brain size={18} />
            </button>
            <button className="btn btn-ghost btn-sm btn-icon" onClick={exportConversation} title="Export" disabled={messages.length === 0}>
              <Download size={18} />
            </button>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
            {messages.length === 0 && (
              <div className="anim-fade" style={{ textAlign: "center", paddingTop: 80 }}>
                <Bot size={48} style={{ color: "var(--accent)", opacity: 0.5 }} />
                <h2 style={{ color: "var(--t1)", marginTop: 16, fontWeight: 700 }}>Opsora AI Agent</h2>
                <p style={{ color: "var(--t3)", fontSize: 14, maxWidth: 400, margin: "8px auto" }}>
                  Ask me to manage your infrastructure, check deployments, or analyze system metrics.
                </p>

                {/* Quick Actions */}
                <div className="qa-grid" style={{ marginTop: 32 }}>
                  {quickActions.map((qa) => (
                    <button
                      key={qa.label}
                      className="qa-btn anim-slide"
                      disabled={isRunning}
                      onClick={() => {
                        setInput(qa.goal);
                        setTimeout(() => inputRef.current?.focus(), 50);
                      }}
                    >
                      <qa.icon size={20} style={{ color: "var(--accent)" }} />
                      <span>{qa.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => {
              if (m.role === "user") {
                return (
                  <div key={m.id} className="bubble-user anim-fade">
                    {m.text}
                  </div>
                );
              }

              if (m.role === "thinking") {
                return (
                  <div key={m.id} className="bubble-agent anim-fade" style={{ display: "flex", gap: 12, marginBottom: 12 }}>
                    <div className="bubble-agent-icon"><Bot size={18} /></div>
                    <div className="thinking"><span /><span /><span /></div>
                  </div>
                );
              }

              if (m.role === "tool") {
                return (
                  <div key={m.id} className={`tool-block anim-fade ${m.toolStatus === "approved" ? "approved" : m.toolStatus === "refused" ? "refused" : ""}`}>
                    <div className="tool-name">
                      <span style={{ fontWeight: 600 }}>{m.toolName}</span>
                      {m.toolStatus === "approved" && <CheckCircle size={14} style={{ color: "var(--ok)", marginLeft: 8 }} />}
                      {m.toolStatus === "refused" && <XCircle size={14} style={{ color: "var(--err)", marginLeft: 8 }} />}
                    </div>
                    {m.toolParams && <pre className="tool-params mono">{m.toolParams}</pre>}
                    {m.toolStatus === "pending" && (
                      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="act-approve" onClick={() => handleActionResponse(m.id, true)}>Approve</button>
                        <button className="act-refuse" onClick={() => handleActionResponse(m.id, false)}>Refuse</button>
                      </div>
                    )}
                  </div>
                );
              }

              /* agent */
              return (
                <div key={m.id} className="bubble-agent anim-fade" style={{ display: "flex", gap: 12, marginBottom: 12 }}>
                  <div className="bubble-agent-icon"><Bot size={18} /></div>
                  <div
                    className="bubble-agent-body"
                    dangerouslySetInnerHTML={{ __html: formatMd(m.text) }}
                  />
                </div>
              );
            })}

            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div style={{ padding: "12px 16px", borderTop: "1px solid var(--s2)", background: "var(--s0)" }}>
            {systemHealth && messages.length === 0 && (
              <div style={{ fontSize: 11, color: "var(--t3)", marginBottom: 8 }}>
                Server: {systemHealth.hostname} | CPU: {systemHealth.cpu}% | {systemHealth.instances} instances
              </div>
            )}
            <div className="input-bar" style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
              <span className="model-pill mono">opsora-v2</span>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask the agent..."
                disabled={isRunning}
                rows={1}
                style={{
                  flex: 1,
                  background: "var(--s1)",
                  border: "1px solid var(--s2)",
                  borderRadius: 8,
                  padding: "10px 14px",
                  color: "var(--t1)",
                  fontSize: 14,
                  fontFamily: "var(--sans)",
                  resize: "none",
                  outline: "none",
                  minHeight: 42,
                  maxHeight: 120,
                }}
              />
              <button
                className="btn btn-primary"
                onClick={sendMessage}
                disabled={isRunning || !input.trim()}
                style={{ display: "flex", alignItems: "center", gap: 6, padding: "10px 18px" }}
              >
                {isRunning ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
                {isRunning ? "Running" : "Send"}
              </button>
            </div>
          </div>
        </div>

        {/* ===== Memory Panel ===== */}
        {showMemory && (
          <aside
            className="anim-fade"
            style={{
              width: 300,
              minWidth: 300,
              borderLeft: "1px solid var(--s2)",
              background: "var(--s0)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--s2)", display: "flex", alignItems: "center", gap: 8 }}>
              <Brain size={18} style={{ color: "var(--accent)" }} />
              <span style={{ fontWeight: 700, fontSize: 14, color: "var(--t1)" }}>Agent Memories</span>
              <span className="tag tag-info" style={{ marginLeft: "auto", fontSize: 11 }}>
                {memories?.length ?? 0}
              </span>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
              {memories?.map((mem) => (
                <div
                  key={mem.id}
                  className="panel"
                  style={{ margin: "4px 12px", padding: "10px 12px" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: "var(--t1)", flex: 1 }} className="truncate">
                      {mem.name}
                    </span>
                    <span className={`tag ${mem.type === "user" ? "tag-ok" : mem.type === "feedback" ? "tag-err" : "tag-info"}`} style={{ fontSize: 10 }}>
                      {mem.type}
                    </span>
                    <button
                      className="btn btn-ghost btn-sm btn-icon"
                      onClick={() => deleteMemory(mem.id)}
                      title="Delete memory"
                      style={{ padding: 2 }}
                    >
                      <Trash2 size={14} style={{ color: "var(--err)" }} />
                    </button>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--t3)", marginTop: 4 }}>
                    {mem.description}
                  </div>
                </div>
              ))}
              {(!memories || memories.length === 0) && (
                <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--t3)", fontSize: 13 }}>
                  No memories stored
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
    </Layout>
  );
}
