"use client";
import { Layout } from "@/app/components/Layout";
import {
  Terminal,
  LayoutDashboard,
  Bot,
  Building2,
  MessageCircle,
  Workflow,
  Users,
  Sparkles,
  ExternalLink,
  Cloud,
  GitBranch,
  Box,
  Cpu,
  Zap,
} from "lucide-react";

/* ── Stats ── */
const STATS = [
  { value: "15", label: "Projects" },
  { value: "14", label: "Containers" },
  { value: "24", label: "Models" },
  { value: "0", label: "Instances" },
  { value: "28", label: "API Endpoints" },
  { value: "6", label: "Skills" },
];

/* ── Products ── */
const PRODUCTS = [
  {
    name: "Opsora CLI",
    desc: "Terminal AI assistant with multi-provider routing",
    icon: Terminal,
    color: "var(--accent)",
    bg: "var(--accent-dim)",
    status: "ACTIVE",
    href: "#",
  },
  {
    name: "Opsora Dashboard",
    desc: "Web infrastructure manager with real-time monitoring",
    icon: LayoutDashboard,
    color: "var(--accent2)",
    bg: "var(--accent2-dim)",
    status: "ACTIVE",
    href: "#",
  },
  {
    name: "Opsora Agent",
    desc: "Autonomous AI agent with tool-use and memory",
    icon: Bot,
    color: "#10b981",
    bg: "rgba(16,185,129,0.12)",
    status: "ACTIVE",
    href: "/ai",
  },
  {
    name: "Opsora Agency",
    desc: "AI automation service for business workflows",
    icon: Building2,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.12)",
    status: "ACTIVE",
    href: "#",
  },
  {
    name: "Opsora Chat",
    desc: "Open WebUI integration for conversational AI",
    icon: MessageCircle,
    color: "#ec4899",
    bg: "rgba(236,72,153,0.12)",
    status: "ACTIVE",
    href: "#",
  },
  {
    name: "Opsora Workflows",
    desc: "n8n automation for no-code workflow building",
    icon: Workflow,
    color: "#8b5cf6",
    bg: "var(--accent-dim)",
    status: "ACTIVE",
    href: "#",
  },
  {
    name: "DPRD Platform",
    desc: "Constituent management and legislative tracking",
    icon: Users,
    color: "var(--accent2)",
    bg: "var(--accent2-dim)",
    status: "ACTIVE",
    href: "#",
  },
  {
    name: "Super Agent Hub",
    desc: "No-code agent builder with visual orchestration",
    icon: Sparkles,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.12)",
    status: "BETA",
    href: "#",
  },
];

/* ── Connected Services ── */
const SERVICES = [
  {
    name: "NVIDIA NIM",
    detail: "14 models",
    icon: Cpu,
    status: "ok" as const,
  },
  {
    name: "Alibaba DashScope",
    detail: "3 models",
    icon: Cloud,
    status: "ok" as const,
  },
  {
    name: "Groq",
    detail: "7 models",
    icon: Zap,
    status: "ok" as const,
  },
  {
    name: "Ollama Local",
    detail: "7 models · 37GB",
    icon: Box,
    status: "ok" as const,
  },
  {
    name: "AWS",
    detail: "3 profiles",
    icon: Cloud,
    status: "ok" as const,
  },
  {
    name: "Graphify",
    detail: "8470 nodes",
    icon: GitBranch,
    status: "ok" as const,
  },
];

export default function WorkspacePage() {
  return (
    <Layout>
      <div style={{ padding: "24px 0" }}>
        {/* Header */}
        <div style={{ marginBottom: 20 }}>
          <h1
            style={{
              fontFamily: "var(--mono)",
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: 2,
              color: "var(--accent)",
              margin: 0,
            }}
          >
            WORKSPACE
          </h1>
          <p
            style={{
              fontSize: 12,
              color: "var(--t3)",
              marginTop: 4,
            }}
          >
            Unified view of the entire Opsora ecosystem
          </p>
        </div>

        {/* Stats Row */}
        <div className="data-grid" style={{ marginBottom: 24 }}>
          {STATS.map((s) => (
            <div key={s.label} className="data-cell">
              <div className="data-val">{s.value}</div>
              <div className="data-label">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Products Section */}
        <div style={{ marginBottom: 24 }}>
          <div className="sec-head">
            <span className="sec-title">Products</span>
            <span className="sec-count">{PRODUCTS.length} total</span>
          </div>
          <div className="panel">
            {PRODUCTS.map((p) => {
              const Icon = p.icon;
              return (
                <div key={p.name} className="panel-row">
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      flex: 1,
                      minWidth: 0,
                    }}
                  >
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "var(--r-sm)",
                        background: p.bg,
                        color: p.color,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <Icon size={16} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: "var(--t1)",
                        }}
                      >
                        {p.name}
                      </div>
                      <div
                        className="truncate"
                        style={{
                          fontSize: 11,
                          color: "var(--t3)",
                        }}
                      >
                        {p.desc}
                      </div>
                    </div>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      flexShrink: 0,
                    }}
                  >
                    <span
                      className={
                        p.status === "BETA" ? "tag tag-info" : "tag tag-ok"
                      }
                    >
                      {p.status}
                    </span>
                    <a
                      href={p.href}
                      className="btn btn-ghost btn-sm"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <ExternalLink size={12} />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Connected Services */}
        <div>
          <div className="sec-head">
            <span className="sec-title">Connected Services</span>
            <span className="sec-count">{SERVICES.length} active</span>
          </div>
          <div className="panel">
            {SERVICES.map((svc) => {
              const Icon = svc.icon;
              return (
                <div key={svc.name} className="panel-row">
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                    }}
                  >
                    <span className={`dot dot-${svc.status}`} />
                    <Icon size={14} style={{ color: "var(--t3)" }} />
                    <span
                      style={{
                        fontSize: 13,
                        fontWeight: 500,
                        color: "var(--t1)",
                      }}
                    >
                      {svc.name}
                    </span>
                  </div>
                  <span
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 11,
                      color: "var(--t3)",
                    }}
                  >
                    {svc.detail}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Layout>
  );
}
