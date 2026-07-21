"use client";
import { useState } from "react";
import { Layout } from "@/app/components/Layout";
import {
  Cloud,
  Key,
  Shield,
  ChevronRight,
  Terminal,
  Fingerprint,
  Info,
  CheckCircle2,
  Cpu,
  CreditCard,
  BarChart3,
  Bell,
  Trash2,
  Plus,
  Eye,
  EyeOff,
} from "lucide-react";
import { apiUrl, getHeaders } from "@/app/api/api";
import useSWR from "swr";

/* ── static data ── */
const PROVIDERS = [
  { name: "AWS", status: "configured", tag: "tag-ok", active: false, key: "AKIA••••••••EXAMPLE" },
  { name: "GCP", status: "configured", tag: "tag-ok", active: false, key: "gcp-sa••••••@proj.iam" },
  { name: "NVIDIA", status: "active", tag: "tag-info", active: true, key: "nvapi-••••••••••••" },
  { name: "Groq", status: "active", tag: "tag-info", active: true, key: "gsk_••••••••••••" },
  { name: "DashScope", status: "configured", tag: "tag-ok", active: false, key: "sk-••••••••••••" },
];

const SYSTEM_INFO = [
  { label: "Version", value: "1.0.0" },
  { label: "Build", value: "2026.07.21" },
  { label: "Framework", value: "Next.js 14" },
  { label: "Backend", value: "FastAPI" },
];

/* ── SWR fetcher ── */
const swrFetcher = (url: string) =>
  fetch(apiUrl(url), { headers: getHeaders() }).then((r) => r.json());

/* ── usage mock (replace with real API) ── */
const USAGE = { used: 45_200, limit: 100_000, cost: 2.34 };
const COST_BREAKDOWN = [
  { label: "Total Input", value: "32.1K tokens" },
  { label: "Total Output", value: "13.1K tokens" },
  { label: "Est. Cost", value: `$${USAGE.cost.toFixed(2)}` },
];

export default function SettingsPage() {
  const [sshKey, setSshKey] = useState("");
  const currentModel = "NVIDIA Llama-3.1-70B";

  /* expanded provider */
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});

  /* alerts */
  const { data: alerts = [], mutate: mutateAlerts } = useSWR<
    { id: number; type: string; target: string; events: string[] }[]
  >("/api/v1/alerts", swrFetcher, { fallbackData: [] });

  const [newAlertType, setNewAlertType] = useState("whatsapp");
  const [newAlertTarget, setNewAlertTarget] = useState("");

  const addAlert = async () => {
    if (!newAlertTarget.trim()) return;
    await fetch(apiUrl("/api/v1/alerts"), {
      method: "POST",
      headers: { ...getHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({
        type: newAlertType,
        target: newAlertTarget,
        events: ["agent_done", "instance_error"],
      }),
    });
    setNewAlertTarget("");
    mutateAlerts();
  };

  const deleteAlert = async (id: number) => {
    await fetch(apiUrl(`/api/v1/alerts/${id}`), {
      method: "DELETE",
      headers: getHeaders(),
    });
    mutateAlerts();
  };

  const usagePct = Math.min((USAGE.used / USAGE.limit) * 100, 100);

  return (
    <Layout>
      <div
        style={{
          maxWidth: 720,
          margin: "0 auto",
          padding: "32px 20px",
          display: "flex",
          flexDirection: "column",
          gap: 32,
        }}
      >
        {/* ── 1. Usage & Billing ── */}
        <section>
          <div className="sec-head">
            <CreditCard size={16} style={{ color: "var(--accent)" }} />
            <span className="sec-title">Usage &amp; Billing</span>
          </div>
          <div className="panel">
            <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* token bar */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontFamily: "var(--mono)",
                    fontSize: 12,
                    color: "var(--t2)",
                    marginBottom: 6,
                  }}
                >
                  <span>
                    {(USAGE.used / 1000).toFixed(1)}K / {(USAGE.limit / 1000).toFixed(0)}K tokens today
                  </span>
                  <span>{usagePct.toFixed(0)}%</span>
                </div>
                <div
                  style={{
                    height: 6,
                    borderRadius: 3,
                    background: "var(--s3)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${usagePct}%`,
                      height: "100%",
                      borderRadius: 3,
                      background: "var(--accent)",
                      transition: "width 0.4s ease",
                    }}
                  />
                </div>
              </div>

              {/* data-grid */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 10,
                }}
              >
                {COST_BREAKDOWN.map((item) => (
                  <div
                    key={item.label}
                    style={{
                      background: "var(--s3)",
                      borderRadius: "var(--r-sm)",
                      padding: "10px 12px",
                    }}
                  >
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 10,
                        color: "var(--t3)",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        marginBottom: 4,
                      }}
                    >
                      {item.label}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 14,
                        color: "var(--t1)",
                        fontWeight: 600,
                      }}
                    >
                      {item.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── 2. Provider Credentials ── */}
        <section>
          <div className="sec-head">
            <Cloud size={16} style={{ color: "var(--accent)" }} />
            <span className="sec-title">Provider Credentials</span>
          </div>
          <div className="panel">
            {PROVIDERS.map((p, i) => (
              <div key={p.name}>
                <div
                  className="panel-row"
                  style={{
                    cursor: "pointer",
                    borderBottom:
                      i < PROVIDERS.length - 1 ? "1px solid var(--s2)" : "none",
                  }}
                  onClick={() =>
                    setExpanded(expanded === p.name ? null : p.name)
                  }
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                    }}
                  >
                    <span
                      className={`dot ${p.active ? "dot-ok" : "dot-warn"}`}
                    />
                    <span
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 13,
                        color: "var(--t1)",
                      }}
                    >
                      {p.name}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className={`tag ${p.tag}`}>{p.status}</span>
                    <ChevronRight
                      size={14}
                      style={{
                        color: "var(--t3)",
                        transform:
                          expanded === p.name ? "rotate(90deg)" : "rotate(0)",
                        transition: "transform 0.15s",
                      }}
                    />
                  </div>
                </div>

                {/* expanded key */}
                {expanded === p.name && (
                  <div
                    style={{
                      padding: "8px 16px 12px",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      background: "var(--s1)",
                    }}
                  >
                    <Key size={12} style={{ color: "var(--t3)" }} />
                    <span
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 12,
                        color: "var(--t2)",
                        flex: 1,
                      }}
                    >
                      {showKey[p.name]
                        ? p.key.replace(/•/g, "x")
                        : p.key}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowKey((prev) => ({
                          ...prev,
                          [p.name]: !prev[p.name],
                        }));
                      }}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "var(--t3)",
                        padding: 2,
                      }}
                    >
                      {showKey[p.name] ? (
                        <EyeOff size={13} />
                      ) : (
                        <Eye size={13} />
                      )}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* ── 3. Alerts & Notifications ── */}
        <section>
          <div className="sec-head">
            <Bell size={16} style={{ color: "var(--accent)" }} />
            <span className="sec-title">Alerts &amp; Notifications</span>
          </div>
          <div className="panel">
            <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {/* existing alerts */}
              {alerts.map((a) => (
                <div
                  key={a.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "8px 10px",
                    background: "var(--s3)",
                    borderRadius: "var(--r-sm)",
                  }}
                >
                  <Info size={14} style={{ color: "var(--accent)", flexShrink: 0 }} />
                  <span
                    className="tag tag-neutral"
                    style={{ textTransform: "capitalize" }}
                  >
                    {a.type}
                  </span>
                  <span
                    style={{
                      flex: 1,
                      fontFamily: "var(--mono)",
                      fontSize: 12,
                      color: "var(--t1)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {a.target}
                  </span>
                  {a.events?.map((ev) => (
                    <span key={ev} className="tag tag-info" style={{ fontSize: 10 }}>
                      {ev}
                    </span>
                  ))}
                  <button
                    onClick={() => deleteAlert(a.id)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      color: "var(--err, #f87171)",
                      padding: 2,
                    }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}

              {/* add new */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginTop: 4,
                }}
              >
                <select
                  value={newAlertType}
                  onChange={(e) => setNewAlertType(e.target.value)}
                  className="input"
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 12,
                    padding: "6px 8px",
                    background: "var(--s3)",
                    color: "var(--t1)",
                    border: "1px solid var(--b1)",
                    borderRadius: "var(--r-sm)",
                  }}
                >
                  <option value="whatsapp">WhatsApp</option>
                  <option value="telegram">Telegram</option>
                  <option value="email">Email</option>
                </select>
                <input
                  className="input input-mono"
                  placeholder="target (number / email)"
                  value={newAlertTarget}
                  onChange={(e) => setNewAlertTarget(e.target.value)}
                  style={{ flex: 1, fontSize: 12, padding: "6px 10px" }}
                />
                <button
                  onClick={addAlert}
                  className="btn btn-sm btn-primary"
                  style={{ display: "flex", alignItems: "center", gap: 4 }}
                >
                  <Plus size={13} />
                  Add
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* ── 4. AI Model ── */}
        <section>
          <div className="sec-head">
            <Cpu size={16} style={{ color: "var(--accent)" }} />
            <span className="sec-title">AI Model</span>
          </div>
          <div className="panel">
            <div className="panel-row">
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <Terminal size={14} style={{ color: "var(--accent)" }} />
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 13,
                    color: "var(--t2)",
                  }}
                >
                  Current model
                </span>
              </div>
              <span className="model-pill">{currentModel}</span>
            </div>
          </div>
        </section>

        {/* ── 5. System ── */}
        <section>
          <div className="sec-head">
            <Terminal size={16} style={{ color: "var(--accent)" }} />
            <span className="sec-title">System</span>
          </div>
          <div className="panel">
            {SYSTEM_INFO.map((item, i) => (
              <div
                key={item.label}
                className="panel-row"
                style={{
                  borderBottom:
                    i < SYSTEM_INFO.length - 1
                      ? "1px solid var(--s2)"
                      : "none",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 13,
                    color: "var(--t2)",
                  }}
                >
                  {item.label}
                </span>
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 13,
                    color: "var(--t1)",
                  }}
                >
                  {item.value}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ── 6. About ── */}
        <div
          style={{
            textAlign: "center",
            padding: "16px 0",
            color: "var(--t3)",
            fontFamily: "var(--mono)",
            fontSize: 12,
            opacity: 0.6,
          }}
        >
          Opsora — multi-cloud infrastructure management
        </div>
      </div>
    </Layout>
  );
}
