"use client";
import { useState } from "react";
import { Layout } from "@/app/components/Layout";
import {
  Server,
  Terminal,
  Database,
  Brain,
  Globe,
  Shield,
  BarChart3,
  FileText,
  HardDrive,
  Code,
  Cloud,
  Cpu,
  Boxes,
  GitBranch,
  Search,
  Zap,
} from "lucide-react";

type Mode = "servers" | "tools" | "skills" | "resources";

const MODES: { key: Mode; label: string }[] = [
  { key: "servers", label: "MCP Servers" },
  { key: "tools", label: "Tools" },
  { key: "skills", label: "Skills" },
  { key: "resources", label: "Resources" },
];

/* ── MCP Servers ── */
const MCP_SERVERS = [
  {
    name: "Graphify",
    desc: "Code knowledge graph — semantic search across all indexed codebases",
    icon: GitBranch,
    color: "var(--accent)",
    bg: "var(--accent-dim)",
    status: "connected",
    meta: ["8470 nodes", "15203 edges"],
  },
  {
    name: "Opsora Proxy",
    desc: "AI model router — unified access to multiple LLM providers",
    icon: Globe,
    color: "var(--accent2)",
    bg: "var(--accent2-dim)",
    status: "connected",
    meta: ["24 models", "3 providers"],
  },
  {
    name: "System Monitor",
    desc: "Real-time server metrics and health monitoring",
    icon: Cpu,
    color: "#10b981",
    bg: "rgba(16,185,129,0.12)",
    status: "connected",
    meta: ["CPU", "RAM", "Disk", "Docker"],
  },
  {
    name: "Memory Store",
    desc: "Persistent agent memory with full-text search and retrieval",
    icon: Brain,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.12)",
    status: "connected",
    meta: ["persistent", "cross-session"],
  },
];

/* ── Agent Tools ── */
const TOOLS = [
  {
    name: "run_command",
    desc: "Execute shell commands via SSH on managed instances",
    icon: Terminal,
    color: "var(--accent)",
    bg: "var(--accent-dim)",
    note: "Destructive commands require approval",
  },
  {
    name: "list_instances",
    desc: "List all managed servers with current state",
    icon: Server,
    color: "var(--accent2)",
    bg: "var(--accent2-dim)",
    note: "Returns status, tags, metadata",
  },
  {
    name: "get_logs",
    desc: "Tail and search server logs in real time",
    icon: FileText,
    color: "#10b981",
    bg: "rgba(16,185,129,0.12)",
    note: "journalctl or syslog",
  },
  {
    name: "system_health",
    desc: "Local server metrics — CPU, RAM, disk, services",
    icon: BarChart3,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.12)",
    note: "CPU, RAM, disk, services",
  },
  {
    name: "memory_search",
    desc: "Search agent memory with full-text queries",
    icon: Search,
    color: "#ec4899",
    bg: "rgba(236,72,153,0.12)",
    note: "Full-text search across entries",
  },
  {
    name: "memory_add",
    desc: "Save entries to persistent agent memory",
    icon: Brain,
    color: "#8b5cf6",
    bg: "var(--accent-dim)",
    note: "Persists across sessions",
  },
  {
    name: "graphify_query",
    desc: "Query the code knowledge graph for semantic search",
    icon: GitBranch,
    color: "var(--accent2)",
    bg: "var(--accent2-dim)",
    note: "Semantic code search",
  },
  {
    name: "provision_instance",
    desc: "Create and configure new cloud server instances",
    icon: Cloud,
    color: "#10b981",
    bg: "rgba(16,185,129,0.12)",
    note: "AWS, GCP, DO, Vultr",
  },
];

/* ── Agent Skills ── */
const SKILLS = [
  {
    name: "Infrastructure Audit",
    desc: "Full health check across all managed instances — services, uptime, resource usage",
    icon: Shield,
    color: "#10b981",
    bg: "rgba(16,185,129,0.12)",
    tags: ["automated", "scheduled"],
  },
  {
    name: "Deploy Pipeline",
    desc: "Git pull → build → deploy → verify with rollback on failure",
    icon: Zap,
    color: "var(--accent)",
    bg: "var(--accent-dim)",
    tags: ["git", "ci/cd"],
  },
  {
    name: "Security Scan",
    desc: "Check for vulnerabilities, open ports, pending security updates",
    icon: Shield,
    color: "#ef4444",
    bg: "rgba(239,68,68,0.12)",
    tags: ["security", "audit"],
  },
  {
    name: "Performance Analysis",
    desc: "CPU/RAM/disk trends, bottleneck detection, optimization suggestions",
    icon: BarChart3,
    color: "var(--accent2)",
    bg: "var(--accent2-dim)",
    tags: ["metrics", "trends"],
  },
  {
    name: "Log Analysis",
    desc: "Parse and summarize recent log entries, flag anomalies and errors",
    icon: FileText,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.12)",
    tags: ["logs", "parsing"],
  },
  {
    name: "Backup & Recovery",
    desc: "Create snapshots, verify integrity, restore from backup on demand",
    icon: HardDrive,
    color: "#8b5cf6",
    bg: "var(--accent-dim)",
    tags: ["backup", "disaster-recovery"],
  },
];

/* ── Workspace Resources ── */
const RESOURCES = [
  {
    name: "Docker Containers",
    desc: "Running containers across all services",
    icon: Boxes,
    color: "var(--accent2)",
    bg: "var(--accent2-dim)",
    meta: ["14 running"],
    detail: "ollama, webui, n8n, qdrant, …",
  },
  {
    name: "AI Models",
    desc: "Available models across all providers",
    icon: Brain,
    color: "var(--accent)",
    bg: "var(--accent-dim)",
    meta: ["24 available"],
    detail: "NVIDIA 14 · Alibaba 3 · Groq 7",
  },
  {
    name: "Projects",
    desc: "Codebases indexed in graphify knowledge graph",
    icon: Code,
    color: "#10b981",
    bg: "rgba(16,185,129,0.12)",
    meta: ["15 indexed"],
    detail: "Full semantic search",
  },
  {
    name: "Cloud Accounts",
    desc: "Connected cloud infrastructure providers",
    icon: Cloud,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.12)",
    meta: ["3 providers"],
    detail: "AWS (3 profiles) · GCP · DO",
  },
  {
    name: "Databases",
    desc: "Running database engines",
    icon: Database,
    color: "#ec4899",
    bg: "rgba(236,72,153,0.12)",
    meta: ["3 engines"],
    detail: "PostgreSQL 16 · Redis 7 · Qdrant",
  },
  {
    name: "Services",
    desc: "Self-hosted applications and proxies",
    icon: Globe,
    color: "#8b5cf6",
    bg: "var(--accent-dim)",
    meta: ["6 active"],
    detail: "Open WebUI · n8n · Guacamole · Caddy",
  },
];

export default function CatalogPage() {
  const [mode, setMode] = useState<Mode>("servers");

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
            CATALOG
          </h1>
          <p
            style={{
              fontSize: 12,
              color: "var(--t3)",
              marginTop: 4,
            }}
          >
            MCP servers, tools, skills, and resources available to the agent
          </p>
        </div>

        {/* Mode Bar */}
        <div className="mode-bar" style={{ marginBottom: 20 }}>
          {MODES.map((m) => (
            <button
              key={m.key}
              className={`mode-btn${mode === m.key ? " active" : ""}`}
              onClick={() => setMode(m.key)}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* MCP Servers */}
        {mode === "servers" && (
          <div>
            <div className="sec-head">
              <span className="sec-title">MCP Servers</span>
              <span className="sec-count">{MCP_SERVERS.length} connected</span>
            </div>
            <div className="catalog-grid">
              {MCP_SERVERS.map((s) => {
                const Icon = s.icon;
                return (
                  <div key={s.name} className="catalog-card">
                    <div
                      className="catalog-icon"
                      style={{ background: s.bg, color: s.color }}
                    >
                      <Icon size={18} />
                    </div>
                    <div className="catalog-name">{s.name}</div>
                    <div className="catalog-desc">{s.desc}</div>
                    <div className="catalog-meta">
                      <span className="tag tag-ok">{s.status}</span>
                      {s.meta.map((m) => (
                        <span key={m} className="tag tag-neutral">
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tools */}
        {mode === "tools" && (
          <div>
            <div className="sec-head">
              <span className="sec-title">Agent Tools</span>
              <span className="sec-count">{TOOLS.length} available</span>
            </div>
            <div className="catalog-grid">
              {TOOLS.map((t) => {
                const Icon = t.icon;
                return (
                  <div key={t.name} className="catalog-card">
                    <div
                      className="catalog-icon"
                      style={{ background: t.bg, color: t.color }}
                    >
                      <Icon size={18} />
                    </div>
                    <div
                      className="catalog-name"
                      style={{ fontFamily: "var(--mono)", fontSize: 13 }}
                    >
                      {t.name}
                    </div>
                    <div className="catalog-desc">{t.desc}</div>
                    <div className="catalog-meta">
                      <span className="tag tag-info">{t.note}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Skills */}
        {mode === "skills" && (
          <div>
            <div className="sec-head">
              <span className="sec-title">Agent Skills</span>
              <span className="sec-count">{SKILLS.length} configured</span>
            </div>
            <div className="catalog-grid">
              {SKILLS.map((sk) => {
                const Icon = sk.icon;
                return (
                  <div key={sk.name} className="catalog-card">
                    <div
                      className="catalog-icon"
                      style={{ background: sk.bg, color: sk.color }}
                    >
                      <Icon size={18} />
                    </div>
                    <div className="catalog-name">{sk.name}</div>
                    <div className="catalog-desc">{sk.desc}</div>
                    <div className="catalog-meta">
                      {sk.tags.map((tg) => (
                        <span key={tg} className="tag tag-neutral">
                          {tg}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Resources */}
        {mode === "resources" && (
          <div>
            <div className="sec-head">
              <span className="sec-title">Workspace Resources</span>
              <span className="sec-count">{RESOURCES.length} categories</span>
            </div>
            <div className="catalog-grid">
              {RESOURCES.map((r) => {
                const Icon = r.icon;
                return (
                  <div key={r.name} className="catalog-card">
                    <div
                      className="catalog-icon"
                      style={{ background: r.bg, color: r.color }}
                    >
                      <Icon size={18} />
                    </div>
                    <div className="catalog-name">{r.name}</div>
                    <div className="catalog-desc">{r.desc}</div>
                    <div className="catalog-meta">
                      {r.meta.map((m) => (
                        <span key={m} className="tag tag-ok">
                          {m}
                        </span>
                      ))}
                      <span className="tag tag-neutral">{r.detail}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
