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
  const [form, setForm] = useState({ name: "", host: "", port: "22", user: "root" });
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!form.name || !form.host) return;
    setCreating(true);
    try {
      await instancesApi.create({
        name: form.name,
        host: form.host,
        port: parseInt(form.port, 10) || 22,
        ssh_user: form.user,
        status: "unknown",
        tags: [],
        metadata: {},
        team_id: 1,
      } as any);
      setShowCreate(false);
      setForm({ name: "", host: "", port: "22", user: "root" });
      mutate();
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const total = instances?.length ?? 0;
  const online = instances?.filter((i) => i.status === "up").length ?? 0;

  return (
    <Layout>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 style={{ color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "16px", letterSpacing: "1px" }}>
            INSTANCES
          </h1>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="btn btn-primary btn-icon"
            style={{ borderRadius: "var(--r-sm)" }}
          >
            {showCreate ? <X size={16} /> : <Plus size={16} />}
          </button>
        </div>

        {/* Metrics */}
        <div className="data-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          <div className="data-cell">
            <div className="data-val">{isLoading ? "—" : total}</div>
            <div className="data-label">Total</div>
          </div>
          <div className="data-cell">
            <div className="data-val" style={{ color: "var(--ok)" }}>{isLoading ? "—" : online}</div>
            <div className="data-label">Online</div>
          </div>
          <div className="data-cell">
            <div className="data-val" style={{ color: "var(--err)" }}>{isLoading ? "—" : total - online}</div>
            <div className="data-label">Offline</div>
          </div>
        </div>

        {/* Create form */}
        {showCreate && (
          <div className="panel anim-slide">
            <div className="panel-head">
              <span>New Instance</span>
            </div>
            <div className="panel-body space-y-3">
              <input
                className="input"
                placeholder="Instance name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              <input
                className="input input-mono"
                placeholder="Host / IP address"
                value={form.host}
                onChange={(e) => setForm({ ...form, host: e.target.value })}
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="input input-mono"
                  placeholder="Port"
                  value={form.port}
                  onChange={(e) => setForm({ ...form, port: e.target.value })}
                />
                <input
                  className="input"
                  placeholder="SSH user"
                  value={form.user}
                  onChange={(e) => setForm({ ...form, user: e.target.value })}
                />
              </div>
              <button
                disabled={creating || !form.name || !form.host}
                onClick={handleCreate}
                className="btn btn-primary w-full"
              >
                {creating && <Loader2 size={14} className="animate-spin" />}
                Add Instance
              </button>
            </div>
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skel" style={{ height: 52 }} />
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="panel" style={{ borderColor: "rgba(248,81,73,0.3)" }}>
            <div className="panel-body text-[13px]" style={{ color: "var(--err)" }}>
              {error.message}
            </div>
          </div>
        )}

        {/* Instance list */}
        {instances && (
          <div className="panel">
            <div className="sec-head" style={{ padding: "10px 14px" }}>
              <span className="sec-title">All Instances</span>
              <span className="sec-count">{total}</span>
            </div>
            {instances.length === 0 ? (
              <div className="panel-body text-center" style={{ padding: "32px 14px", color: "var(--t3)" }}>
                <Server size={24} style={{ margin: "0 auto 8px", opacity: 0.3 }} />
                <div className="text-[13px]">No instances registered</div>
                <div className="text-[11px] mt-1">Press + to add your first server</div>
              </div>
            ) : (
              instances.map((inst: Instance) => (
                <div
                  key={inst.id}
                  className="inst-row"
                  onClick={() => router.push(`/instances/${inst.id}`)}
                >
                  <div className="inst-icon">
                    <Server size={14} style={{ color: "var(--accent)" }} />
                  </div>
                  <div className="inst-meta">
                    <div className="inst-name">{inst.name}</div>
                    <div className="inst-sub">
                      {inst.host}:{inst.port} · {inst.ssh_user}
                    </div>
                  </div>
                  <StatusBadge status={inst.status} />
                </div>
              ))
            )}
          </div>
        )}

        <div className="spacer-b" />
      </div>
    </Layout>
  );
}
