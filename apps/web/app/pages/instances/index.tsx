/* Instances page — premium mobile-first */
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useInstances } from "@/app/hooks/useApi";
import { instancesApi } from "@/app/api/api";
import { Layout } from "@/app/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Server, Plus, Loader2, X } from "lucide-react";
import type { Instance } from "@/app/types";

export default function InstancesPage() {
  const router = useRouter();
  const { data: instances, error, isLoading, mutate } = useInstances();
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createHost, setCreateHost] = useState("");
  const [createPort, setCreatePort] = useState("22");
  const [createUser, setCreateUser] = useState("root");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!createName || !createHost) return;
    setCreating(true);
    try {
      await instancesApi.create({
        name: createName,
        host: createHost,
        port: parseInt(createPort, 10) || 22,
        ssh_user: createUser,
        status: "unknown",
        tags: [],
        metadata: {},
        team_id: 1,
      } as any);
      setShowCreate(false);
      setCreateName(""); setCreateHost(""); setCreatePort("22"); setCreateUser("root");
      mutate();
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const total = instances?.length ?? 0;
  const online = instances?.filter((i) => i.status === "up").length ?? 0;
  const offline = instances?.filter((i) => i.status === "down").length ?? 0;

  return (
    <Layout>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold gradient-text">Instances</h1>
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary btn w-10 h-10 !p-0 rounded-xl">
            {showCreate ? <X size={18} /> : <Plus size={18} />}
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Total", val: total, color: "text-white" },
            { label: "Online", val: online, color: "text-emerald-400" },
            { label: "Offline", val: offline, color: "text-red-400" },
          ].map((s) => (
            <div key={s.label} className="card-glass text-center py-3">
              <div className={`text-xl font-bold ${s.color}`}>{isLoading ? "..." : s.val}</div>
              <div className="text-[11px] text-slate-500 font-medium mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Create form — slide-up on mobile */}
        {showCreate && (
          <div className="card animate-slide-up space-y-3">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Add Instance</div>
            <input className="input text-sm" placeholder="Name *" value={createName} onChange={(e) => setCreateName(e.target.value)} />
            <input className="input text-sm" placeholder="Host/IP *" value={createHost} onChange={(e) => setCreateHost(e.target.value)} />
            <div className="grid grid-cols-2 gap-2">
              <input className="input text-sm" placeholder="Port" value={createPort} onChange={(e) => setCreatePort(e.target.value)} />
              <input className="input text-sm" placeholder="SSH User" value={createUser} onChange={(e) => setCreateUser(e.target.value)} />
            </div>
            <button disabled={creating || !createName || !createHost} onClick={handleCreate} className="btn btn-primary w-full">
              {creating && <Loader2 size={16} className="animate-spin" />}
              Save Instance
            </button>
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-slate-800/40 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {/* Error */}
        {error && <div className="card border-red-800/50 bg-red-900/10 text-red-400 text-sm">{error.message}</div>}

        {/* Instance grid */}
        {instances && (
          <div className="space-y-3">
            {instances.length === 0 && (
              <div className="text-center py-12 text-sm text-slate-600">
                <Server size={32} className="mx-auto mb-3 opacity-30" />
                No instances yet. Tap + to add one.
              </div>
            )}
            {instances.map((inst: Instance) => (
              <div
                key={inst.id}
                className="card-glass cursor-pointer active:scale-[0.98] transition-transform"
                onClick={() => router.push(`/instances/${inst.id}`)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <Server size={16} className="text-brand-400" />
                    <span className="font-semibold text-sm text-white">{inst.name}</span>
                  </div>
                  <StatusBadge status={inst.status} />
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span className="font-mono">{inst.host}:{inst.port}</span>
                  <span className="text-slate-700">|</span>
                  <span>{inst.ssh_user}</span>
                </div>
                {inst.tags && inst.tags.length > 0 && (
                  <div className="flex gap-1.5 mt-2 flex-wrap">
                    {inst.tags.map((t: string) => (
                      <span key={t} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}