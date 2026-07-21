"use client";

import { useInstances } from "@/app/hooks/useApi";
import { Layout } from "@/app/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Server, Wifi, WifiOff, Cpu } from "lucide-react";

export default function DashboardPage() {
  const { data: instances, error, isLoading } = useInstances();

  const total = instances?.length ?? 0;
  const online = instances?.filter((i) => i.status === "up").length ?? 0;
  const offline = total - online;
  const agentJobs = instances?.filter((i) => i.tags?.includes("agent")).length ?? 0;

  return (
    <Layout>
      <div className="anim-fade">
        {/* Page header */}
        <div className="sec-head">
          <h1 className="sec-title">Activity Overview</h1>
          {isLoading && <span className="tag tag-neutral">loading</span>}
        </div>

        {/* Metrics grid */}
        <div className="data-grid">
          <div className="data-cell">
            <div className="data-val">
              {isLoading ? <span className="skel" style={{ width: 32 }} /> : total}
            </div>
            <div className="data-label">
              <Server size={12} /> Total Instances
            </div>
          </div>

          <div className="data-cell">
            <div className="data-val" style={{ color: "var(--ok)" }}>
              {isLoading ? <span className="skel" style={{ width: 24 }} /> : online}
            </div>
            <div className="data-label">
              <Wifi size={12} /> Online
            </div>
          </div>

          <div className="data-cell">
            <div className="data-val" style={{ color: "var(--err)" }}>
              {isLoading ? <span className="skel" style={{ width: 24 }} /> : offline}
            </div>
            <div className="data-label">
              <WifiOff size={12} /> Offline
            </div>
          </div>

          <div className="data-cell">
            <div className="data-val" style={{ color: "var(--accent)" }}>
              {isLoading ? <span className="skel" style={{ width: 24 }} /> : agentJobs}
            </div>
            <div className="data-label">
              <Cpu size={12} /> Agent Jobs
            </div>
          </div>
        </div>

        {/* Instance list */}
        <div className="panel" style={{ marginTop: "1.5rem" }}>
          <div className="panel-head">
            <div className="sec-head">
              <h2 className="sec-title">Instances</h2>
              {total > 0 && <span className="sec-count">{total}</span>}
            </div>
          </div>

          <div className="panel-body">
            {/* Loading state */}
            {isLoading && (
              <>
                {[0, 1, 2].map((i) => (
                  <div key={i} className="inst-row">
                    <span className="skel" style={{ width: 8, height: 8, borderRadius: "50%" }} />
                    <div className="inst-meta">
                      <span className="skel" style={{ width: 120, height: 14 }} />
                      <span className="skel" style={{ width: 80, height: 10 }} />
                    </div>
                  </div>
                ))}
              </>
            )}

            {/* Error state */}
            {error && (
              <div className="log-block" style={{ color: "var(--err)" }}>
                ✗ {error.message}
              </div>
            )}

            {/* Empty state */}
            {!isLoading && !error && instances?.length === 0 && (
              <div className="log-block">
                <span style={{ color: "var(--t3)" }}>
                  $ no instances registered
                </span>
                <br />
                <span style={{ color: "var(--t2)", fontSize: "0.8rem" }}>
                  Connect your first agent via Settings → API Keys
                </span>
              </div>
            )}

            {/* Instance rows */}
            {instances?.map((inst) => {
              const isUp = inst.status === "up";
              return (
                <div key={inst.id} className="inst-row">
                  <span className={`dot ${isUp ? "dot-ok dot-pulse" : "dot-err"}`} />
                  <div className="inst-meta">
                    <span className="inst-name">{inst.name}</span>
                    <span className="inst-sub">
                      {inst.host}:{inst.port}
                      {inst.ssh_user && ` · ${inst.ssh_user}`}
                    </span>
                  </div>
                  <StatusBadge status={inst.status} />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Layout>
  );
}
