/* Commands runner — multi-instance command execution UI */
"use client";
import { useState } from "react";
import { useInstances } from "@/app/hooks/useApi";
import { Layout } from "@/app/components/Layout";
import { commandsApi } from "@/app/api/api";
import { Terminal, Loader2, CheckCircle, XCircle } from "lucide-react";
import type { Instance } from "@/app/types";

export default function CommandsPage() {
  const { data: instances } = useInstances();
  const [selected, setSelected] = useState<number[]>([]);
  const [command, setCommand] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const toggle = (id: number) => {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  };

  const run = async () => {
    if (!command || selected.length === 0) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await commandsApi.run(selected, command);
      setResult(res);
    } catch (err) {
      setResult({ error: String(err) });
    } finally {
      setRunning(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Command Runner</h1>

        {/* Instance selector — horizontal scroll on mobile */}
        <div>
          <h2 className="text-sm font-semibold text-slate-400 mb-2 flex items-center gap-2">
            <Terminal size={14} /> Targets {selected.length > 0 && <span className="text-brand-400">({selected.length})</span>}
          </h2>
          <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
            {(instances ?? []).map((inst: Instance) => (
              <button
                key={inst.id}
                onClick={() => toggle(inst.id)}
                className={`chip shrink-0 ${
                  selected.includes(inst.id) ? "!border-brand-500 !bg-brand-900/30 !text-white" : ""
                }`}
              >
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    ["up", "running"].includes(inst.status) ? "bg-green-400" : "bg-yellow-400"
                  }`}
                />
                {inst.name}
              </button>
            ))}
          </div>
        </div>

        {/* Command input */}
        <div className="flex gap-2">
          <input
            className="input font-mono text-sm flex-1"
            placeholder="$ ls -la"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                run();
              }
            }}
          />
          <button
            onClick={run}
            disabled={running || !command || selected.length === 0}
            className="btn btn-primary"
          >
            {running ? <Loader2 className="animate-spin" size={18} /> : <Terminal size={18} />}
            Run
          </button>
        </div>

        {/* Result */}
        {result && (
          <div className="card space-y-2 animate-fade-in">
            <div className="flex items-center gap-2">
              {result.error ? (
                <XCircle size={16} className="text-red-400" />
              ) : (
                <CheckCircle size={16} className="text-green-400" />
              )}
              <span className="text-sm font-medium">{result.error ? "Failed" : "Done"}</span>
            </div>
            <pre className="code text-xs text-slate-300 whitespace-pre-wrap max-h-60 overflow-y-auto">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </Layout>
  );
}