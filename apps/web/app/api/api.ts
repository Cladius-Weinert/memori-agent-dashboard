import { getHeaders, apiUrl, useAuthStore } from "@/app/stores/authStore";
import type { Instance, User } from "@/app/types";

// Re-export helpers from authStore for direct use by components
export { getHeaders, apiUrl };

// Generic fetch wrapper with SWR-compatible signature
export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(apiUrl(url), { headers: getHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// Instance API
export const instancesApi = {
  list: () => fetcher<Instance[]>("/api/v1/instances"),
  get: (id: number) => fetcher<Instance>(`/api/v1/instances/${id}`),
  create: (body: Omit<Instance, "id" | "created_at" | "last_checked_at">) =>
    fetch(apiUrl("/api/v1/instances"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  testConnection: (id: number) =>
    fetcher<{ ok: boolean; detail: string }>(`/api/v1/instances/${id}/test-connection`),
};

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const res = await fetch(apiUrl("/api/v1/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data as { access_token: string; token_type: string };
  },
  register: async (data: { email: string; password: string; full_name?: string }) => {
    const res = await fetch(apiUrl("/api/v1/auth/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
    return body as User;
  },
  me: () => fetcher<User>("/api/v1/auth/me"),
};

// Command API
export const commandsApi = {
  run: (instance_ids: number[], command: string) =>
    fetch(apiUrl("/api/v1/commands"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ instance_ids, command }),
    }).then((r) => r.json()),
  get: (id: number) => fetcher<{ outputs: Record<string, unknown> }>(`/api/v1/commands/${id}`),
};

// Agent API
export const agentApi = {
  run: (goal: string) =>
    fetch(apiUrl("/api/v1/agent/run"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ goal }),
    }).then((r) => r.json()),
  getJob: (id: number) =>
    fetcher<{ id: number; status: string; plan: unknown[] }>(`/api/v1/agent/jobs/${id}`),
};

// WebSocket helper — includes auth token as query param
export function wsUrl(instanceId: number): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const wsBase = base.replace(/^http/, "ws");
  const token = useAuthStore.getState().token ?? "";
  return `${wsBase}/ws/terminal/${instanceId}?token=${encodeURIComponent(token)}`;
}