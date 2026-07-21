import { useAuthStore, getHeaders, apiUrl } from "@/app/stores/authStore";
import type { Instance, AgentJob } from "@/app/types";
import useSWR from "swr";

const fetcher = (url: string) =>
  fetch(apiUrl(url), { headers: getHeaders() }).then((r) => {
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  });

export function useInstances() {
  return useSWR<Instance[]>("/api/v1/instances", fetcher);
}

export function useInstance(id: number) {
  return useSWR<Instance>(`/api/v1/instances/${id}`, fetcher);
}

export function useAgentJob(id: number) {
  return useSWR<AgentJob>(`/api/v1/agent/jobs/${id}`, fetcher);
}

export function useCommandsHistory() {
  return useSWR<{ id: number; command: string; status: string }[]>("/api/v1/commands", fetcher);
}