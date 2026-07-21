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
  const [history, setHistory] = useState<{ cmd: string; ok: boolean }[]>([]);

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
      setHistory((h) => [{ cmd: command, ok: !res.error }, ...h].slice(0, 20));
    } catch (err) {
      setResult({ error: String(err) });
      setHistory((h) => [{ cmd: command, ok: false }, ...h].slice(0, 20));
    } finally {
      setRunning(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <h1 style={{ color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "16px", letterSpacing: "1px" }}>
            COMMANDS
          </h1>
          {selected.length > 0 && (
            <span className="tag tag-info">{selected.length} target{selected.length > 1 ? "s" : ""}</span>
          )}
        </div>

        {/* Target selector */}
        <div>
          <div className="sec-head">
            <span className="sec-title">Targets</span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {(instances ?? []).map((inst: Instance) => {
              const active = selected.includes(inst.id);
              return (
                <button
                  key={inst.id}
                  onClick={() => toggle(inst.id)}
                  className="btn btn-ghost btn-sm shrink-0"
                  style={{
                    borderColor: active ? "var(--accent)" : "var(--b1)",
                    background: active ? "var(--accent-dim)" : "transparent",
                    color: active ? "var(--accent)" : "var(--t2)",
                  }}
                >
                  <span
                    className={`dot ${["up", "running"].includes(inst.status) ? "dot-ok" : "dot-warn"}`}
                  />
                  {inst.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Command input */}
        <div className="input-bar">
          <span style={{ color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "12px", paddingLeft: "8px" }}>$</span>
          <input
            className="input-mono"
            placeholder="ls -la /var/log"
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
            className="send-btn"
          >
            {running ? <Loader2 size={14} className="animate-spin" /> : <Terminal size={14} />}
          </button>
        </div>

        {/* Result */}
        {result && (
          <div className="panel anim-fade">
            <div className="panel-head">
              <div className="gap-row">
                {result.error ? (
                  <XCircle size={14} style={{ color: "var(--err)" }} />
                ) : (
                  <CheckCircle size={14} style={{ color: "var(--ok)" }} />
                )}
                <span>{result.error ? "Failed" : "Success"}</span>
              </div>
            </div>
            <div className="log-block" style={{ margin: "0", borderRadius: 0, border: "none", maxHeight: "400px" }}>
              {JSON.stringify(result, null, 2)}
            </div>
          </div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div>
            <div className="sec-head">
              <span className="sec-title">History</span>
              <span className="sec-count">{history.length}</span>
            </div>
            <div className="panel">
              {history.map((h, i) => (
                <div key={i} className="panel-row" style={{ gap: "8px" }}>
                  <span className={`dot ${h.ok ? "dot-ok" : "dot-err"}`} />
                  <span className="mono text-[12px] truncate flex-1" style={{ color: "var(--t2)" }}>
                    {h.cmd}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="spacer-b" />
      </div>
    </Layout>
  );
}
