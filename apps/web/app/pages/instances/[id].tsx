/* Instance detail page — terminal tab, logs, metrics */
"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Layout } from "@/app/components/Layout";
import { Terminal, FileText, Activity } from "lucide-react";
import { instancesApi, wsUrl } from "@/app/api/api";
import type { Instance } from "@/app/types";

export default function InstanceDetailPage({ params }: { params: { id: string } }) {
  const id = parseInt(params.id, 10);
  const [tab, setTab] = useState<"terminal" | "logs" | "metrics" | "files">("terminal");
  const [inst, setInst] = useState<Instance | null>(null);
  const [cmdResult, setCmdResult] = useState<string>("");

  useEffect(() => {
    instancesApi.get(id).then(setInst).catch(console.error);
  }, [id]);

  const runCmd = async (cmd: string) => {
    try {
      const res = await fetch(`/api/v1/instances/${id}/run-command?command=${encodeURIComponent(cmd)}`);
      const data = await res.json();
      setCmdResult(data.stdout ?? data.stderr ?? "no output");
    } catch (err) {
      setCmdResult(`Error: ${err}`);
    }
  };

  return (
    <Layout>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{inst?.name ?? `Instance #${id}`}</h1>
        <div className="text-sm text-slate-400">{inst?.host}:{inst?.port}</div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-slate-800">
          {[
            { key: "terminal", label: "Terminal", icon: Terminal },
            { key: "logs", label: "Logs", icon: FileText },
            { key: "metrics", label: "Metrics", icon: Activity },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm ${
                tab === t.key ? "text-white border-b-2 border-brand-500" : "text-slate-400 hover:text-white"
              }`}
            >
              <t.icon size={14} />
              {t.label}
            </button>
          ))}
        </div>

        {/* Terminal tab */}
        {tab === "terminal" && (
          <div className="space-y-3">
            <div className="bg-slate-900 rounded-lg p-4 font-mono text-xs text-green-400 h-48 overflow-auto">
              {cmdResult || "Run a command to see output here"}
            </div>
            <div className="flex gap-2">
              <input
                className="flex-1 px-3 py-2 bg-slate-800 rounded border border-slate-700 text-sm font-mono"
                placeholder="ls -la"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    runCmd((e.target as HTMLInputElement).value);
                    (e.target as HTMLInputElement).value = "";
                  }
                }}
              />
            </div>
          </div>
        )}

        {/* Metrics tab */}
        {tab === "metrics" && (
          <div className="p-4 bg-slate-800/40 rounded-lg text-sm text-slate-400">
            CPU/RAM/Disk metrics will appear here once monitoring is configured.
          </div>
        )}

        {/* Logs tab */}
        {tab === "logs" && (
          <div className="p-4 bg-slate-800/40 rounded-lg text-sm text-slate-400">
            Real-time log viewer coming soon.
          </div>
        )}
      </div>
    </Layout>
  );
}