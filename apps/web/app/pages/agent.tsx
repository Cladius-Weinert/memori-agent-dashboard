/* Agent chat — input goal, see step timeline, approve/refuse */
"use client";
import { useState } from "react";
import { agentApi } from "@/app/api/api";
import { Layout } from "@/app/components/Layout";
import { Bot, Loader2, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import type { AgentJob, AgentAction } from "@/app/types";
import useSWR from "swr";

export default function AgentPage() {
  const [goal, setGoal] = useState("");
  const [running, setRunning] = useState(false);
  const [job, setJob] = useState<AgentJob | null>(null);
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [actionsPending, setActionsPending] = useState<AgentAction[]>([]);

  const run = async () => {
    if (!goal) return;
    setRunning(true);
    try {
      const res = (await agentApi.run(goal)) as any;
      setJob(res);
      // Poll for actions
      const poll = setInterval(async () => {
        try {
          const actionsRes = await fetch(`/api/v1/agent/actions?job_id=${res.id}`);
          const data = await actionsRes.json();
          setActions(data ?? []);
          setActionsPending((data ?? []).filter((a: AgentAction) => a.requires_approval));
        } catch { /* noop */ }
      }, 2000);
      setTimeout(() => clearInterval(poll), 60000);
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(false);
    }
  };

  const approve = async (id: number) => {
    await fetch(`/api/v1/agent/actions/${id}/approve`, { method: "POST" });
    setActionsPending((prev) => prev.filter((a) => a.id !== id));
  };

  const refuse = async (id: number) => {
    await fetch(`/api/v1/agent/actions/${id}/refuse`, { method: "POST" });
    setActionsPending((prev) => prev.filter((a) => a.id !== id));
  };

  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Agent</h1>

        {/* Input */}
        <div className="flex gap-3">
          <input
            className="flex-1 px-4 py-3 bg-slate-900 rounded-lg border border-slate-700 text-sm"
            placeholder="What should the agent do?"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                run();
              }
            }}
          />
          <button
            onClick={run}
            disabled={running || !goal}
            className="px-6 py-3 bg-brand-600 hover:bg-brand-700 rounded-lg text-sm font-medium flex items-center gap-2"
          >
            {running ? <Loader2 className="animate-spin" size={16} /> : <Bot size={16} />}
            Run
          </button>
        </div>

        {/* Job status */}
        {job && (
          <div className="p-4 bg-slate-800/60 rounded-lg border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`w-3 h-3 rounded-full ${
                  job.status === "done"
                    ? "bg-green-400"
                    : job.status === "failed"
                    ? "bg-red-400"
                    : "bg-yellow-400 animate-pulse"
                }`}
              />
              <span className="font-medium text-sm">{job.status}</span>
            </div>
            <div className="text-xs text-slate-400">ID: {job.id}</div>
          </div>
        )}

        {/* Actions requiring approval */}
        {actionsPending.length > 0 && (
          <div className="p-4 bg-yellow-900/30 rounded-lg border border-yellow-700 space-y-3">
            <div className="flex items-center gap-2 text-yellow-400">
              <AlertTriangle size={16} />
              <span className="font-semibold text-sm">
                {actionsPending.length} action(s) require approval
              </span>
            </div>
            {actionsPending.map((a) => (
              <div key={a.id} className="flex items-center justify-between bg-slate-800/40 p-3 rounded">
                <div className="text-sm">
                  <span className="text-brand-400">{a.tool}</span>
                  <pre className="text-xs text-slate-400 mt-1">{JSON.stringify(a.params, null, 2)}</pre>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => approve(a.id)}
                    className="px-3 py-1 bg-green-800/50 hover:bg-green-700 text-green-300 rounded text-xs flex items-center gap-1"
                  >
                    <CheckCircle size={12} /> Approve
                  </button>
                  <button
                    onClick={() => refuse(a.id)}
                    className="px-3 py-1 bg-red-800/50 hover:bg-red-700 text-red-300 rounded text-xs flex items-center gap-1"
                  >
                    <XCircle size={12} /> Refuse
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Timeline */}
        {actions.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-slate-400">Execution Timeline</h2>
            {actions.map((a) => (
              <div
                key={a.id}
                className="flex items-start gap-3 p-3 bg-slate-800/40 rounded border border-slate-700/60"
              >
                <div className="mt-0.5">
                  <div className={`w-3 h-3 rounded-full ${a.result.error ? "bg-red-400" : "bg-green-400"}`} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-brand-400">{a.tool}</span>
                    {a.requires_approval && (
                      <span className="text-xs text-yellow-400">⚠️ needs approval</span>
                    )}
                  </div>
                  <pre className="text-xs text-slate-400 mt-1">{JSON.stringify(a.params, null, 2)}</pre>
                  <div className="text-xs text-slate-500 mt-1">{new Date(a.created_at).toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}