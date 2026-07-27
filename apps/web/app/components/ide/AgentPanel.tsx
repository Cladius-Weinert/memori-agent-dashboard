"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bot, Send, Loader2, CheckCircle, XCircle, ListChecks, Terminal,
} from "lucide-react";
import { ModelPicker } from "@/components/ModelPicker";
import { agentApi, conversationsApi } from "@/app/api/api";
import {
  approveAction,
  refuseAction,
  streamAgentJob,
  type AgentStreamEvent,
} from "@/app/lib/agentStream";

type PlanStep = { tool: string; args?: Record<string, unknown> };
type StepView = {
  tool: string;
  result: Record<string, unknown>;
  requires_approval: boolean;
  action_id?: number;
  status?: "pending" | "approved" | "refused";
};
type Msg = {
  id: string;
  role: "user" | "agent";
  content: string;
  plan?: PlanStep[];
  steps?: StepView[];
  loading?: boolean;
};

const uid = () => Math.random().toString(36).slice(2, 10);

export function AgentPanel() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState("nvidia-llama-70b");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    conversationsApi.list().then((list) => {
      if (list[0]) setConversationId(list[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs]);

  const patchAgent = (id: string, patch: Partial<Msg>) => {
    setMsgs((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  };

  const handleStream = (agentId: string, jobId: number) => {
    streamAgentJob(jobId, (ev: AgentStreamEvent) => {
      if (ev.type === "plan") {
        patchAgent(agentId, { plan: ev.plan });
      }
      if (ev.type === "step") {
        setMsgs((prev) => prev.map((m) => {
          if (m.id !== agentId) return m;
          const steps = [...(m.steps ?? []), {
            tool: ev.tool,
            result: ev.result,
            requires_approval: ev.requires_approval,
            action_id: ev.action_id,
            status: ev.requires_approval ? "pending" as const : undefined,
          }];
          return { ...m, steps };
        }));
      }
      if (ev.type === "message") {
        patchAgent(agentId, { content: ev.content, loading: false });
      }
      if (ev.type === "done") {
        patchAgent(agentId, { loading: false });
        setLoading(false);
      }
    });
  };

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setLoading(true);

    const userId = uid();
    const agentId = uid();
    setMsgs((prev) => [
      ...prev,
      { id: userId, role: "user", content: text },
      { id: agentId, role: "agent", content: "", loading: true, steps: [] },
    ]);

    try {
      let convId = conversationId;
      if (!convId) {
        const conv = await conversationsApi.create("Opsora Chat", selectedModel);
        convId = conv.id;
        setConversationId(convId);
      }

      const job = await agentApi.run(text, { conversation_id: convId, model: selectedModel });
      handleStream(agentId, job.id);
    } catch (err) {
      patchAgent(agentId, {
        content: `Error: ${err instanceof Error ? err.message : String(err)}`,
        loading: false,
      });
      setLoading(false);
    }
  };

  const onApprove = async (msgId: string, actionId: number) => {
    await approveAction(actionId);
    setMsgs((prev) => prev.map((m) => {
      if (m.id !== msgId || !m.steps) return m;
      return {
        ...m,
        steps: m.steps.map((s) =>
          s.action_id === actionId ? { ...s, status: "approved" } : s,
        ),
      };
    }));
  };

  const onRefuse = async (msgId: string, actionId: number) => {
    await refuseAction(actionId);
    setMsgs((prev) => prev.map((m) => {
      if (m.id !== msgId || !m.steps) return m;
      return {
        ...m,
        steps: m.steps.map((s) =>
          s.action_id === actionId ? { ...s, status: "refused" } : s,
        ),
      };
    }));
  };

  return (
    <div className="ide-agent">
      <div className="ide-agent-header">
        <Bot size={16} />
        <span>Opsora Agent</span>
        <ModelPicker selected={selectedModel} onSelect={setSelectedModel} />
      </div>

      <div className="ide-agent-messages" ref={scrollRef}>
        {msgs.length === 0 && (
          <div className="ide-agent-empty">
            <p>Cursor-style agent untuk coding & infra.</p>
            <ul>
              <li>Analisis codebase</li>
              <li>Edit file dengan approval</li>
              <li>Jalankan perintah di instance</li>
            </ul>
          </div>
        )}
        {msgs.map((m) => (
          <div key={m.id} className={`ide-msg ide-msg--${m.role}`}>
            {m.role === "user" ? (
              <p>{m.content}</p>
            ) : (
              <>
                {m.plan && m.plan.length > 0 && (
                  <div className="ide-plan">
                    <ListChecks size={13} /> Plan ({m.plan.length} steps)
                    {m.plan.map((s, i) => (
                      <div key={i} className="ide-plan-step">{i + 1}. {s.tool}</div>
                    ))}
                  </div>
                )}
                {m.steps?.map((s, i) => (
                  <div key={i} className="ide-tool-block">
                    <Terminal size={12} /> <strong>{s.tool}</strong>
                    <pre>{JSON.stringify(s.result, null, 2).slice(0, 400)}</pre>
                    {s.requires_approval && s.action_id && s.status === "pending" && (
                      <div className="ide-approval">
                        <button type="button" onClick={() => onApprove(m.id, s.action_id!)}>
                          <CheckCircle size={12} /> Approve
                        </button>
                        <button type="button" onClick={() => onRefuse(m.id, s.action_id!)}>
                          <XCircle size={12} /> Refuse
                        </button>
                      </div>
                    )}
                  </div>
                ))}
                {m.loading && <Loader2 size={14} className="animate-spin" />}
                {m.content && <p>{m.content}</p>}
              </>
            )}
          </div>
        ))}
      </div>

      <div className="ide-agent-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="Tanya agent… (Enter kirim, Shift+Enter baris baru)"
          rows={3}
        />
        <button type="button" onClick={send} disabled={loading || !input.trim()}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
    </div>
  );
}
