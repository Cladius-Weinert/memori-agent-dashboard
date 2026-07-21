/* Dashboard — instance overview, stats, recent activity */
"use client";
import { useInstances } from "@/app/hooks/useApi";
import { Server, Loader2, AlertCircle, Activity } from "lucide-react";
import { Layout } from "@/app/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";

export default function DashboardPage() {
  const { data: instances, error, isLoading } = useInstances();

  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>

        {/* Stats cards */}
        <div className="grid grid-cols-3 gap-3">
          <div className="card-glass text-center">
            <div className="text-xl md:text-2xl font-bold text-white">
              {isLoading ? "..." : instances?.length ?? 0}
            </div>
            <div className="text-xs text-slate-400 mt-1">Total</div>
          </div>
          <div className="card-glass text-center">
            <div className="text-xl md:text-2xl font-bold text-green-400">
              {instances?.filter((i) => i.status === "up").length ?? 0}
            </div>
            <div className="text-xs text-slate-400 mt-1">Online</div>
          </div>
          <div className="card-glass text-center">
            <div className="text-xl md:text-2xl font-bold text-red-400">
              {instances?.filter((i) => i.status === "down").length ?? 0}
            </div>
            <div className="text-xs text-slate-400 mt-1">Offline</div>
          </div>
        </div>

        {/* Instance list */}
        <div>
          <h2 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><Activity size={14} /> Live Instances</h2>
          {isLoading && (
            <div className="flex items-center gap-2 text-slate-400">
              <Loader2 className="animate-spin" size={16} />
              Loading...
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle size={16} />
              {error.message}
            </div>
          )}
          {instances && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {instances.map((inst) => (
                <div
                  key={inst.id}
                  className="p-4 bg-slate-800/40 rounded-lg border border-slate-700/60 hover:border-brand-500/30 transition"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Server size={16} className="text-brand-500" />
                      <span className="font-medium text-white text-sm">{inst.name}</span>
                    </div>
                    <StatusBadge status={inst.status} />
                  </div>
                  <div className="text-xs text-slate-500">
                    {inst.host}:{inst.port} · {inst.ssh_user}
                  </div>
                  <div className="mt-2 text-xs text-slate-400 truncate">
                    {inst.tags?.join(", ")}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}