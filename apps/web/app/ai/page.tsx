/* Opsora — Premium AI Agent Interface */
"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Layout } from "@/app/components/Layout";
import { ModelPicker } from "@/components/ModelPicker";
import {
  Bot,
  Send,
  Loader2,
  CheckCircle,
  XCircle,
  Sparkles,
  Terminal,
  FileText,
  Server,
  Globe,
  HardDrive,
  RefreshCw,
} from "lucide-react";
import { getHeaders, apiUrl } from "@/app/api/api";

/* ─── Types ─── */
type Msg = {
  role: "user" | "agent";
  content: string;
  actions?: Action[];
  done?: boolean;
  id: string;
};
type Action = {
  id: number;
  tool: string;
  params: Record<string, unknown>;
  result: Record<string, unknown>;
  requires_approval: boolean;
  approved_by?: number;
  status?: "pending" | "approved" | "refused";
};

const QUICK_ACTIONS = [
  { label: "Check all servers", icon: Globe, desc: "Ping & status" },
  { label: "Show disk usage", icon: HardDrive, desc: "df -h" },
  { label: "System update", icon: RefreshCw, desc: "apt update" },
  { label: "Deploy app", icon: Sparkles, desc: "Git pull + build" },
];

let msgId = 0;
const uid = () => `m-${++msgId}`;

/* ─── Tool execution icon ─── */
const toolIcon = (tool: string) => {
  if (tool.includes("list") || tool.includes("status")) return <Server size={12} />;
  if (tool.includes("command") || tool.includes("run")) return <Terminal size={12} />;
  if (tool.includes("log")) return <FileText size={12} />;
  return <Bot size={12} />;
};

/* ─── Component ─── */
export default function OpsoraPage() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "agent", content: "Halo, saya **Opsora**.\n\nKatakan apa yang perlu dilakukan — cek server, deploy, update, atau kelola infrastruktur Anda.", id: uid() },
  ]);
  const [input, setInput] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [selectedModel, setSelectedModel] = useState("nvidia-llama");
  const [jobId, setJobId] = useState<number | null>(null);
  const chatEnd = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* Auto scroll */
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  /* Cleanup polling */
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  /* ─── Poll job actions ─── */
  const startPolling = useCallback((jobId: number, msgIdx: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(apiUrl(`/api/v1/agent/jobs/${jobId}`), { headers: getHeaders() });
        const data = await res.json();
        setMessages((prev) => {
          const updated = [...prev];
          const m = updated[msgIdx];
          if (!m) return prev;
          updated[msgIdx] = {
            ...m,
            actions: (data.actions ?? []).map((a: Action) => ({
              ...a,
              status: a.approved_by ? "approved" : a.result?.refused ? "refused" : "pending" as const,
            })),
          };
          if (data.status === "completed" || data.status === "failed") {
            updated[msgIdx] = { ...updated[msgIdx], done: true };
          }
          return updated;
        });
        if (data.status === "completed" || data.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          setIsRunning(false);
        }
      } catch { /* retry */ }
    }, 2000);
  }, []);

  /* ─── Send ─── */
  const send = useCallback(async (text?: string) => {
    const goal = text ?? input;
    if (!goal.trim() || isRunning) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: goal, id: uid() }]);
    setIsRunning(true);

    const thinkingId = uid();
    const thinkingIdx = messages.length + 1;
    setMessages((prev) => [...prev, { role: "agent", content: "🧠", actions: [], id: thinkingId }]);

    try {
      const res = await fetch(apiUrl("/api/v1/agent/run"), {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({ goal, model_id: selectedModel }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Gagal");
      const data = await res.json();
      setJobId(data.id);

      const planStr = data.plan?.length
        ? `📋 **Rencana** (${data.plan.length} langkah):\n${data.plan.map((s: any, i: number) => `  ${i + 1}. \`${s.tool}\` ${JSON.stringify(s.args ?? {})}`).join("\n")}`
        : "";

      setMessages((prev) => {
        const updated = [...prev];
        updated[thinkingIdx] = {
          role: "agent",
          content: `✅ **Goal diterima**\n\n${goal}${planStr ? `\n\n${planStr}` : ""}`,
          actions: [],
          id: thinkingId,
        };
        return updated;
      });

      startPolling(data.id, thinkingIdx);
    } catch (err: unknown) {
      setIsRunning(false);
      const msg = err instanceof Error ? err.message : "Gagal terhubung ke Opsora";
      setMessages((prev) => {
        const updated = [...prev];
        updated[thinkingIdx] = { role: "agent", content: `❌ ${msg}`, id: thinkingId };
        return updated;
      });
    }
  }, [input, isRunning, selectedModel, messages.length, startPolling]);

  /* ─── Approve/Refuse ─── */
  const handleAction = useCallback(async (actionId: number, approve: boolean) => {
    const endpoint = approve ? "approve" : "refuse";
    try {
      await fetch(apiUrl(`/api/v1/agent/actions/${actionId}/${endpoint}`), {
        method: "POST", headers: getHeaders(),
      });
      setMessages((prev) =>
        prev.map((m) => ({
          ...m,
          actions: m.actions?.map((a) =>
            a.id === actionId ? { ...a, status: approve ? "approved" : "refused" as const } : a
          ),
        }))
      );
    } catch { /* silent */ }
  }, []);

  /* ─── Render ─── */
  return (
    <Layout>
      <div className="flex flex-col h-[calc(100dvh-88px)] md:h-[calc(100vh-64px)] opsora-container">
        {/* ── Header ── */}
        <div className="opsora-header">
          <div className="flex items-center gap-3">
            <div className="opsora-avatar">
              <div className="opsora-avatar-ring" />
              <span className="text-lg font-bold text-white">O</span>
            </div>
            <div>
              <h1 className="text-base font-bold text-white/90 tracking-tight">Opsora</h1>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? "bg-amber-400 animate-pulse" : "bg-emerald-400"}`} />
                <span className="text-[11px] text-slate-500 font-medium">{isRunning ? "Memproses..." : "Siap"}</span>
              </div>
            </div>
          </div>
          <ModelPicker selected={selectedModel} onSelect={setSelectedModel} />
        </div>

        {/* ── Chat ── */}
        <div className="flex-1 overflow-y-auto space-y-2.5 py-3 px-0.5 opsora-chat">
          {messages.map((msg, i) => (
            <div key={msg.id} className={`opsora-bubble-${msg.role} animate-fade-in`}>
              {msg.role === "agent" && (
                <div className="opsora-agent-icon">
                  <Bot size={12} />
                </div>
              )}
              <div className={msg.role === "user" ? "opsora-user-body" : "opsora-agent-body"}>
                {msg.content === "🧠" ? (
                  <div className="flex items-center gap-2 py-1">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span className="text-xs text-slate-500 font-medium">Opsora sedang berpikir...</span>
                  </div>
                ) : (
                  <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                )}

                {/* Actions / tool executions */}
                {msg.actions && msg.actions.length > 0 && (
                  <div className="opsora-actions mt-2">
                    {msg.actions.map((a) => (
                      <div key={a.id} className={`opsora-action ${a.status === "approved" ? "approved" : a.status === "refused" ? "refused" : ""}`}>
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-brand-400 shrink-0">{toolIcon(a.tool)}</span>
                            <span className="text-xs font-mono font-medium text-slate-200 truncate">{a.tool}</span>
                            {a.status === "approved" && <CheckCircle size={12} className="text-emerald-400 shrink-0" />}
                            {a.status === "refused" && <XCircle size={12} className="text-red-400 shrink-0" />}
                          </div>
                          {a.requires_approval && a.status === "pending" && (
                            <div className="flex gap-1.5 shrink-0">
                              <button
                                onClick={() => handleAction(a.id, true)}
                                className="opsora-btn-approve"
                                aria-label="Approve"
                              >
                                <CheckCircle size={14} />
                              </button>
                              <button
                                onClick={() => handleAction(a.id, false)}
                                className="opsora-btn-refuse"
                                aria-label="Refuse"
                              >
                                <XCircle size={14} />
                              </button>
                            </div>
                          )}
                        </div>
                        {Object.keys(a.params).length > 0 && (
                          <pre className="text-[11px] text-slate-600 mt-1.5 truncate font-mono">
                            {JSON.stringify(a.params).slice(0, 120)}
                          </pre>
                        )}
                      </div>
                    ))}
                    {!msg.done && (
                      <div className="flex gap-1 mt-2 pl-1">
                        <span className="w-1 h-1 bg-brand-400/60 rounded-full animate-pulse-dot" />
                        <span className="w-1 h-1 bg-brand-400/60 rounded-full animate-pulse-dot" style={{ animationDelay: "0.2s" }} />
                        <span className="w-1 h-1 bg-brand-400/60 rounded-full animate-pulse-dot" style={{ animationDelay: "0.4s" }} />
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={chatEnd} />
        </div>

        {/* ── Quick actions ── */}
        <div className="opsora-quick-actions">
          {QUICK_ACTIONS.map((qa) => (
            <button
              key={qa.label}
              onClick={() => send(qa.label)}
              disabled={isRunning}
              className="opsora-chip"
            >
              <qa.icon size={14} className="text-brand-400" />
              <div className="text-left">
                <div className="text-xs font-medium text-slate-200">{qa.label}</div>
                <div className="text-[10px] text-slate-600">{qa.desc}</div>
              </div>
            </button>
          ))}
        </div>

        {/* ── Input ── */}
        <div className="opsora-input-area">
          <div className="opsora-input-wrapper">
            <input
              ref={inputRef}
              className="opsora-input"
              placeholder="Ketik perintah..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
              }}
              disabled={isRunning}
            />
            <button
              onClick={() => send()}
              disabled={isRunning || !input.trim()}
              className="opsora-send-btn"
              aria-label="Send"
            >
              {isRunning ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}