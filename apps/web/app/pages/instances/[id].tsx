"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { Layout } from "@/app/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Terminal, FileText, Activity, ArrowLeft } from "lucide-react";
import { instancesApi, wsUrl } from "@/app/api/api";
import { useIDEStore } from "@/app/stores/ideStore";
import type { Instance } from "@/app/types";

const XTermTerminal = dynamic(() => import("@/components/XTermTerminal"), { ssr: false });

type Tab = "terminal" | "logs" | "metrics";

export default function InstanceDetailPage({ params }: { params: { id: string } }) {
  const id = parseInt(params.id, 10);
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("terminal");
  const [inst, setInst] = useState<Instance | null>(null);
  const setTerminalInstanceId = useIDEStore((s) => s.setTerminalInstanceId);

  useEffect(() => {
    instancesApi.get(id).then((i) => {
      setInst(i);
      setTerminalInstanceId(id);
    }).catch(console.error);
    return () => setTerminalInstanceId(null);
  }, [id, setTerminalInstanceId]);

  const TABS: { key: Tab; label: string; icon: typeof Terminal }[] = [
    { key: "terminal", label: "Terminal", icon: Terminal },
    { key: "logs", label: "Logs", icon: FileText },
    { key: "metrics", label: "Metrics", icon: Activity },
  ];

  return (
    <Layout>
      <div className="space-y-4">
        {/* Back + title */}
        <div className="gap-row">
          <button onClick={() => router.push("/instances")} className="btn btn-ghost btn-icon">
            <ArrowLeft size={16} />
          </button>
          <div className="flex-1">
            <div className="gap-row">
              <h1 className="text-[18px]">{inst?.name ?? `Instance #${id}`}</h1>
              {inst && <StatusBadge status={inst.status} />}
            </div>
            {inst && (
              <div className="mono text-[12px] mt-0.5" style={{ color: "var(--t3)" }}>
                {inst.host}:{inst.port} · {inst.ssh_user}
              </div>
            )}
          </div>
        </div>

        {/* Instance info panel */}
        {inst && (
          <div className="data-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" }}>
            <div className="data-cell">
              <div className="data-val text-[16px]">{inst.port}</div>
              <div className="data-label">Port</div>
            </div>
            <div className="data-cell">
              <div className="data-val text-[16px]">{inst.ssh_user}</div>
              <div className="data-label">User</div>
            </div>
            <div className="data-cell">
              <div className="data-val text-[16px]">{inst.tags?.length ?? 0}</div>
              <div className="data-label">Tags</div>
            </div>
            <div className="data-cell">
              <div className="data-val text-[16px]">
                {inst.last_checked_at ? new Date(inst.last_checked_at).toLocaleDateString() : "—"}
              </div>
              <div className="data-label">Last Check</div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-0" style={{ borderBottom: "1px solid var(--b1)" }}>
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className="gap-row"
              style={{
                padding: "8px 14px",
                fontSize: "12px",
                fontWeight: 500,
                fontFamily: "var(--mono)",
                color: tab === t.key ? "var(--accent)" : "var(--t3)",
                background: "none",
                border: "none",
                borderBottom: tab === t.key ? "2px solid var(--accent)" : "2px solid transparent",
                cursor: "pointer",
                transition: "all 0.1s",
              }}
            >
              <t.icon size={13} />
              {t.label}
            </button>
          ))}
        </div>

        {/* Terminal tab */}
        {tab === "terminal" && (
          <div className="space-y-3" style={{ minHeight: "320px" }}>
            <XTermTerminal wsUrl={wsUrl(id)} className="h-[320px]" />
          </div>
        )}

        {/* Metrics tab */}
        {tab === "metrics" && (
          <div className="panel">
            <div className="panel-body" style={{ color: "var(--t3)", textAlign: "center", padding: "32px" }}>
              <Activity size={24} style={{ margin: "0 auto 8px", opacity: 0.3 }} />
              <div className="text-[13px]">Metrics collection not yet configured</div>
              <div className="text-[11px] mt-1">
                Connect Prometheus/Grafana to see CPU, RAM, and disk data
              </div>
            </div>
          </div>
        )}

        {/* Logs tab */}
        {tab === "logs" && (
          <div className="panel">
            <div className="panel-body" style={{ color: "var(--t3)", textAlign: "center", padding: "32px" }}>
              <FileText size={24} style={{ margin: "0 auto 8px", opacity: 0.3 }} />
              <div className="text-[13px]">Real-time log streaming</div>
              <div className="text-[11px] mt-1">Run `journalctl -f` from the Terminal tab</div>
            </div>
          </div>
        )}

        <div className="spacer-b" />
      </div>
    </Layout>
  );
}
