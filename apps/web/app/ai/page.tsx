"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Layout } from "@/app/components/Layout";
import { ModelPicker } from "@/components/ModelPicker";
import {
  Bot, Send, Loader2, CheckCircle, XCircle, Brain, ListChecks, Search,
  Zap, ChevronDown, ChevronRight, Terminal, Database, Globe, FileText,
  HardDrive, Server, Code, BarChart3, PenTool, RefreshCw,
} from "lucide-react";
import { getHeaders, apiUrl } from "@/app/api/api";

/* ── types ── */
type Mode = "chat" | "plan" | "research";
type PlanStep = { text: string; status: "pending" | "running" | "done" | "error"; tool?: string };
type Action = {
  id: number; tool: string; params: Record<string, unknown>;
  result: Record<string, unknown>; requires_approval: boolean;
  approved_by?: number; status?: "pending" | "approved" | "refused";
};
type Delegation = { agent: string; icon: string; color: string; task: string; status: "pending" | "running" | "done" };
type ResearchSource = { name: string; icon: any; status: "searching" | "found" | "analyzed" };
type Msg = {
  role: "user" | "agent";
  content: string;
  thinking?: string;
  thinkingDone?: boolean;
  plan?: PlanStep[];
  actions?: Action[];
  delegations?: Delegation[];
  research?: ResearchSource[];
  done?: boolean;
  id: string;
};

/* ── constants ── */
const QUICK_ACTIONS = [
  { label: "Check all servers", icon: Server, desc: "Status + health" },
  { label: "Analyze codebase", icon: Code, desc: "Graph query" },
  { label: "Deep research: AI trends", icon: Search, desc: "Multi-source" },
  { label: "Plan deployment", icon: ListChecks, desc: "Step by step" },
];

const MCP_TOOLS = [
  { name: "graphify_query", status: "connected" },
  { name: "memory_search", status: "connected" },
  { name: "memory_add", status: "connected" },
  { name: "run_command", status: "connected" },
  { name: "system_health", status: "connected" },
  { name: "list_instances", status: "connected" },
];

const REASONING_CHUNKS = [
  "Parsing user intent and extracting key entities…",
  "Querying knowledge graph for relevant context…",
  "Evaluating available tools and selecting optimal path…",
  "Cross-referencing memory for prior interactions…",
  "Composing response with verified information…",
  "Checking system health and resource availability…",
  "Analyzing code graph for dependency relationships…",
];

const uid = () => Math.random().toString(36).slice(2, 10);

/* ── main component ── */
export default function AIPage() {
  const [mode, setMode] = useState<Mode>("chat");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("qwen-max");
  const scrollRef = useRef<HTMLDivElement>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  /* auto-scroll */
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs]);

  /* cleanup timers on unmount */
  useEffect(() => () => timersRef.current.forEach(clearTimeout), []);

  const later = useCallback((fn: () => void, ms: number) => {
    const t = setTimeout(fn, ms);
    timersRef.current.push(t);
    return t;
  }, []);

  /* patch a message by id */
  const patchMsg = useCallback((id: string, patch: Partial<Msg>) => {
    setMsgs((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }, []);

  /* ── response generator ── */
  function generateResponse(text: string, m: Mode): string {
    const l = text.toLowerCase();
    if (l.includes("server") || l.includes("health")) {
      return "All 3 instances are **healthy**. Primary node uptime: 14d 6h. CPU averaging 23% across the cluster with 61% memory utilization. No anomalies detected in the last 24h monitoring window.";
    }
    if (l.includes("code") || l.includes("analyz")) {
      return "Codebase analysis complete. Found **47 nodes** and **89 edges** across 5 communities. The main module has strong coupling with the auth and data layers. Recommendation: consider extracting the config parser into a standalone module to reduce circular dependencies.";
    }
    if (l.includes("research") || l.includes("trend")) {
      return "Deep research compiled from 5 sources. Key findings:\n\n• **Multi-agent orchestration** is the dominant trend — 73% of enterprise AI deployments now use agent swarms\n• **Reasoning transparency** (chain-of-thought exposure) is expected in production systems\n• **Tool-use standardization** via MCP is gaining rapid adoption\n• **Memory-augmented agents** show 2.4× better task completion rates\n\nAll sources analyzed and cross-referenced. Confidence: high.";
    }
    if (l.includes("plan") || l.includes("deploy")) {
      return "Deployment plan executed successfully. All 5 steps completed:\n\n✅ Requirements gathered — 3 services identified\n✅ Dependencies verified via code graph\n✅ Configuration validated — no conflicts\n✅ Deployment executed — containers restarted\n✅ Health checks passed on all instances\n\nRollback snapshot saved as `snap-20260721-deploy`.";
    }
    return (
      `Understood. I've processed your request about "${text.slice(0, 60)}${text.length > 60 ? "…" : ""}". ` +
      "Based on the available context from memory and the knowledge graph, here's what I found:\n\n" +
      "The system is operating normally. I've logged this interaction and updated the memory index for future reference. " +
      "Let me know if you'd like me to dig deeper into any specific aspect."
    );
  }

  /* ── simulate full agent flow ── */
  const simulateAgent = useCallback(
    (userText: string, currentMode: Mode) => {
      const agentId = uid();
      const lower = userText.toLowerCase();

      const agentMsg: Msg = {
        role: "agent", content: "", id: agentId, done: false,
        thinking: "", thinkingDone: false,
      };
      setMsgs((p) => [...p, agentMsg]);
      setLoading(true);

      let delay = 0;

      /* ── 1. reasoning stream ── */
      const chunks = REASONING_CHUNKS.slice(0, 3 + Math.floor(Math.random() * 3));
      let thinkAccum = "";
      chunks.forEach((chunk, i) => {
        later(() => {
          thinkAccum += (i > 0 ? "\n" : "") + chunk;
          patchMsg(agentId, { thinking: thinkAccum });
        }, delay);
        delay += 350 + Math.random() * 250;
      });
      later(() => patchMsg(agentId, { thinkingDone: true }), delay);
      delay += 250;

      /* ── 2a. plan mode ── */
      const showPlan = currentMode === "plan" || lower.includes("plan") || lower.includes("deploy");
      if (showPlan) {
        const steps: PlanStep[] = [
          { text: "Gathering requirements", status: "pending" },
          { text: "Checking dependencies", status: "pending", tool: "graphify_query" },
          { text: "Validating configuration", status: "pending", tool: "system_health" },
          { text: "Executing deployment", status: "pending", tool: "run_command" },
          { text: "Verifying results", status: "pending" },
        ];
        later(() => patchMsg(agentId, { plan: steps.map((s) => ({ ...s })) }), delay);
        delay += 250;
        steps.forEach((step, i) => {
          later(() => {
            patchMsg(agentId, {
              plan: steps.map((s, j) => ({ ...s, status: (j < i ? "done" : j === i ? "running" : "pending") as PlanStep["status"] })),
            });
          }, delay);
          delay += 550 + Math.random() * 350;
          later(() => {
            patchMsg(agentId, {
              plan: steps.map((s, j) => ({ ...s, status: (j <= i ? "done" : "pending") as PlanStep["status"] })),
            });
          }, delay);
          delay += 150;
        });
      }

      /* ── 2b. research mode ── */
      const showResearch = currentMode === "research" || lower.includes("research");
      if (showResearch) {
        const sources: ResearchSource[] = [
          { name: "Web Search", icon: Globe, status: "searching" },
          { name: "Code Graph", icon: Database, status: "searching" },
          { name: "Memory", icon: HardDrive, status: "searching" },
          { name: "Documentation", icon: FileText, status: "searching" },
          { name: "API Docs", icon: Terminal, status: "searching" },
        ];
        later(() => patchMsg(agentId, { research: sources.map((s) => ({ ...s })) }), delay);
        delay += 350;
        sources.forEach((src, i) => {
          later(() => {
            patchMsg(agentId, {
              research: sources.map((s, j) => ({ ...s, status: (j < i ? "analyzed" : j === i ? "found" : "searching") as ResearchSource["status"] })),
            });
          }, delay);
          delay += 450 + Math.random() * 300;
          later(() => {
            patchMsg(agentId, {
              research: sources.map((s, j) => ({ ...s, status: (j <= i ? "analyzed" : "searching") as ResearchSource["status"] })),
            });
          }, delay);
          delay += 150;
        });
      }

      /* ── 3. tool calls ── */
      const tools: Action[] = [];
      if (lower.includes("server") || lower.includes("health") || lower.includes("check")) {
        tools.push({
          id: 1, tool: "system_health",
          params: { target: "all-instances" },
          result: { status: "healthy", uptime: "14d 6h", cpu: "23%", mem: "61%" },
          requires_approval: false, status: "approved",
        });
      }
      if (lower.includes("code") || lower.includes("analyz") || lower.includes("graph")) {
        tools.push({
          id: 2, tool: "graphify_query",
          params: { query: "find dependencies of main module", limit: 10 },
          result: { nodes: 47, edges: 89, communities: 5 },
          requires_approval: false, status: "approved",
        });
      }
      if (lower.includes("command") || lower.includes("run") || lower.includes("deploy")) {
        tools.push({
          id: 3, tool: "run_command",
          params: { cmd: "docker ps --format json" },
          result: { containers: 4, running: 3, stopped: 1 },
          requires_approval: true, status: "pending",
        });
      }
      if (lower.includes("memory") || lower.includes("remember") || lower.includes("search")) {
        tools.push({
          id: 4, tool: "memory_search",
          params: { query: userText, limit: 5 },
          result: { matches: 3, top_score: 0.94 },
          requires_approval: false, status: "approved",
        });
      }
      if (tools.length === 0) {
        tools.push({
          id: 5, tool: "memory_search",
          params: { query: userText, limit: 3 },
          result: { matches: 2, top_score: 0.87 },
          requires_approval: false, status: "approved",
        });
      }

      later(() => patchMsg(agentId, { actions: [...tools] }), delay);
      delay += 400;

      /* auto-approve pending tools */
      tools.forEach((t) => {
        if (t.requires_approval && t.status === "pending") {
          later(() => {
            patchMsg(agentId, {
              actions: tools.map((a) => (a.id === t.id ? { ...a, status: "approved" as const, approved_by: 1 } : a)),
            });
          }, delay);
          delay += 500;
        }
      });

      /* ── 4. delegations (complex queries) ── */
      if (lower.includes("deep") || lower.includes("research") || lower.includes("full") || lower.includes("plan") || lower.includes("analyze")) {
        const delegations: Delegation[] = [
          { agent: "Researcher", icon: "🔍", color: "#8b5cf6", task: "Gather context from knowledge base", status: "pending" },
          { agent: "Coder", icon: "💻", color: "#06b6d4", task: "Analyze code structure", status: "pending" },
          { agent: "Analyst", icon: "📊", color: "#f59e0b", task: "Evaluate findings", status: "pending" },
          { agent: "Writer", icon: "✍️", color: "#10b981", task: "Compose summary report", status: "pending" },
        ];
        later(() => patchMsg(agentId, { delegations: delegations.map((d) => ({ ...d })) }), delay);
        delay += 350;
        delegations.forEach((d, i) => {
          later(() => {
            patchMsg(agentId, {
              delegations: delegations.map((dd, j) => ({ ...dd, status: (j < i ? "done" : j === i ? "running" : "pending") as Delegation["status"] })),
            });
          }, delay);
          delay += 650 + Math.random() * 350;
          later(() => {
            patchMsg(agentId, {
              delegations: delegations.map((dd, j) => ({ ...dd, status: (j <= i ? "done" : "pending") as Delegation["status"] })),
            });
          }, delay);
          delay += 150;
        });
      }

      /* ── 5. final response ── */
      later(() => {
        patchMsg(agentId, { content: generateResponse(userText, currentMode), done: true });
        setLoading(false);
      }, delay + 350);
    },
    [later, patchMsg]
  );

  /* ── send handler ── */
  const send = useCallback(
    (text?: string) => {
      const msg = (text ?? input).trim();
      if (!msg || loading) return;
      setInput("");
      setMsgs((p) => [...p, { role: "user", content: msg, id: uid() }]);
      simulateAgent(msg, mode);
    },
    [input, loading, mode, simulateAgent]
  );

  /* ── tool action handler ── */
  const handleAction = useCallback((msgId: string, actionId: number, approve: boolean) => {
    setMsgs((prev) =>
      prev.map((m) => {
        if (m.id !== msgId || !m.actions) return m;
        return {
          ...m,
          actions: m.actions.map((a) =>
            a.id === actionId ? { ...a, status: (approve ? "approved" : "refused") as Action["status"] } : a
          ),
        };
      })
    );
  }, []);

  /* ── render: thinking panel ── */
  const ThinkPanel = ({ thinking, thinkingDone }: { thinking?: string; thinkingDone?: boolean }) => {
    const [open, setOpen] = useState(true);
    if (!thinking) return null;
    return (
      <div className={thinkingDone ? "think-panel" : "think-panel think-streaming"} style={{ marginBottom: 8 }}>
        <button className="think-toggle" onClick={() => setOpen(!open)} style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", cursor: "pointer", color: "inherit", padding: 0 }}>
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span style={{ marginLeft: 4, fontSize: 11, fontWeight: 600, letterSpacing: 1, textTransform: "uppercase" as const }}>
            {thinkingDone ? "Thinking" : "Reasoning"}
          </span>
        </button>
        {open && (
          <pre style={{ margin: "8px 0 0", fontSize: 12, fontFamily: "var(--mono)", whiteSpace: "pre-wrap", lineHeight: 1.6, opacity: 0.85 }}>
            {thinking}
            {!thinkingDone && (
              <span className="thinking" style={{ display: "inline-flex", marginLeft: 4 }}>
                <span /><span /><span />
              </span>
            )}
          </pre>
        )}
      </div>
    );
  };

  /* ── render: plan panel ── */
  const PlanPanel = ({ steps }: { steps: PlanStep[] }) => {
    const done = steps.filter((s) => s.status === "done").length;
    return (
      <div className="plan-panel" style={{ marginBottom: 8 }}>
        <div className="plan-head" style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <ListChecks size={14} style={{ color: "var(--accent)" }} />
          <span style={{ fontWeight: 600, fontSize: 12, letterSpacing: 1 }}>PLAN ({done}/{steps.length} steps)</span>
        </div>
        {steps.map((s, i) => (
          <div key={i} className={`plan-step ${s.status === "running" ? "active" : ""}`} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0" }}>
            <span className={`plan-step-icon ${s.status}`}>
              {s.status === "done" && <CheckCircle size={14} style={{ color: "#10b981" }} />}
              {s.status === "error" && <XCircle size={14} style={{ color: "#ef4444" }} />}
              {s.status === "running" && <Loader2 size={14} className="animate-spin" style={{ color: "var(--accent2)" }} />}
              {s.status === "pending" && <span style={{ display: "inline-block", width: 14, height: 14, borderRadius: "50%", border: "2px solid var(--s3)" }} />}
            </span>
            <span className="plan-step-text" style={{ fontSize: 13, opacity: s.status === "pending" ? 0.5 : 1 }}>
              {s.text}
              {s.tool && (
                <code style={{ marginLeft: 6, fontSize: 11, color: "var(--accent2)", fontFamily: "var(--mono)" }}>
                  {s.tool}
                </code>
              )}
            </span>
          </div>
        ))}
      </div>
    );
  };

  /* ── render: delegate grid ── */
  const DelegateGrid = ({ items }: { items: Delegation[] }) => (
    <div className="delegate-grid" style={{ marginBottom: 8 }}>
      {items.map((d, i) => (
        <div key={i} className={`delegate-card ${d.status === "running" ? "running" : d.status === "done" ? "done" : ""}`}>
          <div className="delegate-head" style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              className="delegate-avatar"
              style={{ background: d.color, width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}
            >
              {d.icon}
            </div>
            <span className="delegate-name" style={{ fontWeight: 600, fontSize: 13 }}>{d.agent}</span>
          </div>
          <div className="delegate-task" style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>{d.task}</div>
          <div
            className="delegate-status"
            style={{
              fontSize: 11, marginTop: 4, fontWeight: 600, textTransform: "uppercase" as const,
              letterSpacing: 0.5,
              color: d.status === "done" ? "#10b981" : d.status === "running" ? "var(--accent2)" : "var(--s4)",
            }}
          >
            {d.status === "running" && <Loader2 size={10} className="animate-spin" style={{ marginRight: 4, verticalAlign: "middle" }} />}
            {d.status}
          </div>
        </div>
      ))}
    </div>
  );

  /* ── render: research panel ── */
  const ResearchPanel = ({ sources }: { sources: ResearchSource[] }) => (
    <div className="research-panel" style={{ marginBottom: 8 }}>
      <div className="research-head" style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <Search size={14} style={{ color: "var(--accent2)" }} />
        <span style={{ fontWeight: 600, fontSize: 12, letterSpacing: 1 }}>DEEP RESEARCH</span>
      </div>
      {sources.map((s, i) => {
        const Icon = s.icon;
        return (
          <div key={i} className="research-source" style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0" }}>
            <span
              style={{
                width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                background: s.status === "analyzed" ? "#10b981" : s.status === "found" ? "var(--accent2)" : "var(--s3)",
                transition: "background 0.3s",
              }}
            />
            <Icon size={13} style={{ opacity: 0.6 }} />
            <span style={{ fontSize: 12, flex: 1 }}>{s.name}</span>
            <span style={{ fontSize: 10, opacity: 0.5, fontFamily: "var(--mono)", textTransform: "uppercase" as const }}>
              {s.status === "searching" && "searching…"}
              {s.status === "found" && "found"}
              {s.status === "analyzed" && "✓ analyzed"}
            </span>
          </div>
        );
      })}
    </div>
  );

  /* ── render: tool block ── */
  const ToolBlock = ({ action, msgId }: { action: Action; msgId: string }) => (
    <div className={`tool-block ${action.status === "approved" ? "approved" : action.status === "refused" ? "refused" : ""}`} style={{ margin: "6px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" as const }}>
        <Zap size={12} style={{ color: "var(--accent)", flexShrink: 0 }} />
        <span className="tool-name" style={{ fontWeight: 600, fontSize: 12, color: "var(--accent)" }}>{action.tool}</span>
        <span
          className="tool-params"
          style={{
            fontSize: 11, fontFamily: "var(--mono)", opacity: 0.6,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const, maxWidth: 280,
          }}
        >
          {JSON.stringify(action.params)}
        </span>
        {action.status && (
          <span
            style={{
              marginLeft: "auto", fontSize: 10, fontWeight: 600, textTransform: "uppercase" as const,
              color: action.status === "approved" ? "#10b981" : action.status === "refused" ? "#ef4444" : "var(--s4)",
            }}
          >
            {action.status}
          </span>
        )}
      </div>
      {action.requires_approval && action.status === "pending" && (
        <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
          <button className="act-approve" onClick={() => handleAction(msgId, action.id, true)} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <CheckCircle size={12} /> Approve
          </button>
          <button className="act-refuse" onClick={() => handleAction(msgId, action.id, false)} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <XCircle size={12} /> Refuse
          </button>
        </div>
      )}
      {action.status === "approved" && Object.keys(action.result).length > 0 && (
        <pre style={{ marginTop: 6, fontSize: 11, fontFamily: "var(--mono)", opacity: 0.7, whiteSpace: "pre-wrap" as const }}>
          → {JSON.stringify(action.result, null, 2)}
        </pre>
      )}
    </div>
  );

  /* ── render: formatted text with bold ── */
  const formatText = (text: string) => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} style={{ color: "var(--accent)" }}>{part.slice(2, -2)}</strong>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  /* ================================================================ */
  /*  MAIN RENDER                                                      */
  /* ================================================================ */
  return (
    <Layout>
      <div style={{ display: "flex", flexDirection: "column", height: "100%", maxWidth: 900, margin: "0 auto", padding: "0 16px" }}>

        {/* ── Mode Bar ── */}
        <div className="mode-bar" style={{ display: "flex", gap: 4, padding: "12px 0 8px", justifyContent: "center", alignItems: "center" }}>
          {([
            { key: "chat" as Mode, label: "Chat", icon: Bot },
            { key: "plan" as Mode, label: "Plan", icon: ListChecks },
            { key: "research" as Mode, label: "Research", icon: Search },
          ]).map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={`mode-btn ${mode === key ? (key === "research" ? "research-active" : "active") : ""}`}
              onClick={() => setMode(key)}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}
          <div style={{ marginLeft: 12 }}>
            <ModelPicker selected={selectedModel} onSelect={setSelectedModel} />
          </div>
        </div>

        {/* ── Chat Scroll Area ── */}
        <div ref={scrollRef} className="chat-scroll" style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
          {/* empty state */}
          {msgs.length === 0 && (
            <div style={{ textAlign: "center", padding: "60px 20px" }}>
              <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 64, height: 64, borderRadius: 20, background: "var(--s2)", marginBottom: 16 }}>
                <Brain size={32} style={{ color: "var(--accent)" }} />
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6, color: "var(--s0)" }}>Opsora Agent</h2>
              <p style={{ fontSize: 13, opacity: 0.5, maxWidth: 400, margin: "0 auto 24px" }}>
                AI-powered agent with reasoning visualization, task planning, deep research, and multi-agent delegation.
              </p>
              <div className="qa-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, maxWidth: 440, margin: "0 auto" }}>
                {QUICK_ACTIONS.map((qa, i) => {
                  const Icon = qa.icon;
                  return (
                    <button key={i} className="qa-btn" onClick={() => send(qa.label)}>
                      <Icon size={18} style={{ color: "var(--accent)", flexShrink: 0 }} />
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--s0)" }}>{qa.label}</div>
                        <div style={{ fontSize: 11, opacity: 0.5 }}>{qa.desc}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* messages */}
          {msgs.map((m) => (
            <div key={m.id} style={{ marginBottom: 16 }}>
              {m.role === "user" ? (
                <div className="bubble-user" style={{ display: "flex", justifyContent: "flex-end", padding: "0 8px" }}>
                  <div style={{ background: "var(--accent)", color: "#fff", padding: "10px 16px", borderRadius: "16px 16px 4px 16px", maxWidth: "70%", fontSize: 14, lineHeight: 1.5 }}>
                    {m.content}
                  </div>
                </div>
              ) : (
                <div className="bubble-agent" style={{ display: "flex", gap: 10, padding: "0 8px" }}>
                  <div className="bubble-agent-icon" style={{ width: 32, height: 32, borderRadius: 10, background: "var(--s2)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Bot size={18} style={{ color: "var(--accent)" }} />
                  </div>
                  <div className="bubble-agent-body" style={{ flex: 1, minWidth: 0 }}>
                    {/* Thinking / Reasoning */}
                    <ThinkPanel thinking={m.thinking} thinkingDone={m.thinkingDone} />

                    {/* Plan */}
                    {m.plan && m.plan.length > 0 && <PlanPanel steps={m.plan} />}

                    {/* Research */}
                    {m.research && m.research.length > 0 && <ResearchPanel sources={m.research} />}

                    {/* Delegations */}
                    {m.delegations && m.delegations.length > 0 && <DelegateGrid items={m.delegations} />}

                    {/* Tool calls */}
                    {m.actions && m.actions.map((a) => <ToolBlock key={a.id} action={a} msgId={m.id} />)}

                    {/* Final response text */}
                    {m.content && (
                      <div style={{ fontSize: 14, lineHeight: 1.7, marginTop: 6, whiteSpace: "pre-wrap" as const }}>
                        {formatText(m.content)}
                      </div>
                    )}

                    {/* Loading indicator */}
                    {!m.content && !m.done && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", opacity: 0.5, fontSize: 13 }}>
                        <Loader2 size={14} className="animate-spin" /> Processing…
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* ── MCP Tools Bar ── */}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", padding: "8px 0", justifyContent: "center" }}>
          {MCP_TOOLS.map((t, i) => (
            <span
              key={i}
              className="model-pill"
              style={{
                display: "inline-flex", alignItems: "center", gap: 4,
                padding: "3px 10px", fontSize: 11, fontFamily: "var(--mono)",
                background: "var(--s1)", borderRadius: 6, border: "1px solid var(--s2)",
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: t.status === "connected" ? "#10b981" : "#ef4444" }} />
              {t.name}
            </span>
          ))}
        </div>

        {/* ── Input Bar ── */}
        <div className="input-bar" style={{ display: "flex", gap: 8, padding: "8px 0 16px", alignItems: "center" }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder={
              mode === "plan" ? "Describe what to plan…" :
              mode === "research" ? "What to research…" :
              "Ask the agent…"
            }
            disabled={loading}
            style={{
              flex: 1, padding: "12px 16px", background: "var(--s1)",
              border: "1px solid var(--s2)", borderRadius: 12,
              color: "var(--s0)", fontSize: 14, fontFamily: "var(--sans)", outline: "none",
            }}
          />
          <button
            className="send-btn"
            onClick={() => send()}
            disabled={loading || !input.trim()}
            style={{
              width: 44, height: 44, borderRadius: 12, border: "none",
              background: input.trim() && !loading ? "var(--accent)" : "var(--s2)",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: input.trim() && !loading ? "pointer" : "default",
              transition: "background 0.2s",
            }}
          >
            {loading ? (
              <Loader2 size={18} className="animate-spin" style={{ color: "var(--s4)" }} />
            ) : (
              <Send size={18} style={{ color: input.trim() ? "#fff" : "var(--s4)" }} />
            )}
          </button>
        </div>
      </div>
    </Layout>
  );
}
