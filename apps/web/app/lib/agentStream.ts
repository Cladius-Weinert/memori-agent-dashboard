import { getHeaders, apiUrl } from "@/app/stores/authStore";

export type AgentStreamEvent =
  | { type: "plan"; plan: Array<{ tool: string; args?: Record<string, unknown> }> }
  | { type: "step"; step: number; tool: string; params: Record<string, unknown>; result: Record<string, unknown>; requires_approval: boolean; action_id?: number }
  | { type: "message"; content: string }
  | { type: "done"; status: string };

export function streamAgentJob(
  jobId: number,
  onEvent: (event: AgentStreamEvent) => void,
  onError?: (err: Error) => void,
): () => void {
  const url = apiUrl(`/api/v1/agent/jobs/${jobId}/stream`);
  const source = new EventSource(url);

  source.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data) as AgentStreamEvent;
      onEvent(data);
      if (data.type === "done") source.close();
    } catch (err) {
      onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  };

  source.onerror = () => {
    onError?.(new Error("SSE connection lost"));
    source.close();
  };

  return () => source.close();
}

export async function approveAction(actionId: number): Promise<void> {
  const res = await fetch(apiUrl(`/api/v1/agent/actions/${actionId}/approve`), {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("approve failed");
}

export async function refuseAction(actionId: number): Promise<void> {
  const res = await fetch(apiUrl(`/api/v1/agent/actions/${actionId}/refuse`), {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("refuse failed");
}
