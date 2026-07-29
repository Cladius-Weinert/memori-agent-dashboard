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
  run: (goal: string, opts?: { conversation_id?: number; model?: string; mode?: string }) =>
    fetch(apiUrl("/api/v1/agent/run"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({
        goal,
        conversation_id: opts?.conversation_id,
        model: opts?.model,
        mode: opts?.mode ?? "agent",
      }),
    }).then((r) => r.json()) as Promise<{ id: number; status: string; plan: unknown[] }>,
  getJob: (id: number) =>
    fetcher<{ id: number; status: string; plan: unknown[] }>(`/api/v1/agent/jobs/${id}`),
};

// Files API
export const filesApi = {
  tree: (path = "") => fetcher<{ entries: unknown[] }>(`/api/v1/files/tree?path=${encodeURIComponent(path)}`),
  read: (path: string) => fetcher<{ content: string }>(`/api/v1/files/read?path=${encodeURIComponent(path)}`),
  write: (path: string, content: string) =>
    fetch(apiUrl("/api/v1/files/write"), {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify({ path, content }),
    }).then((r) => r.json()),
  search: (q: string, path = "") =>
    fetcher<{ matches: unknown[] }>(`/api/v1/files/search?q=${encodeURIComponent(q)}&path=${encodeURIComponent(path)}`),
};

// Conversations API
export const conversationsApi = {
  list: () => fetcher<Array<{ id: number; title: string; model: string }>>("/api/v1/conversations"),
  create: (title: string, model = "default") =>
    fetch(apiUrl("/api/v1/conversations"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ title, model }),
    }).then((r) => r.json()) as Promise<{ id: number }>,
  messages: (id: number) =>
    fetcher<Array<{ id: number; role: string; content: string }>>(`/api/v1/conversations/${id}/messages`),
};

// Git API
export const gitApi = {
  status: () => fetcher<{
    branch?: string;
    clean?: boolean;
    staged?: Array<{ path: string; status: string }>;
    unstaged?: Array<{ path: string; status: string }>;
    untracked?: string[];
  }>("/api/v1/git/status"),
  diff: (path = "", staged = false) =>
    fetcher<{ raw?: string; hunks?: Array<{ lines: unknown[] }>; has_changes?: boolean }>(
      `/api/v1/git/diff?path=${encodeURIComponent(path)}&staged=${staged}`,
    ),
  branches: () => fetcher<{ current?: string; branches: string[] }>("/api/v1/git/branches"),
  log: (limit = 15) => fetcher<{ commits: Array<{ hash: string; message: string }> }>(`/api/v1/git/log?limit=${limit}`),
  add: (paths: string[]) =>
    fetch(apiUrl("/api/v1/git/add"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ paths }),
    }).then((r) => r.json()),
  commit: (message: string) =>
    fetch(apiUrl("/api/v1/git/commit"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ message }),
    }).then((r) => {
      if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || "commit failed"); });
      return r.json();
    }),
  checkout: (branch: string) =>
    fetch(apiUrl("/api/v1/git/checkout"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ branch }),
    }).then((r) => r.json()),
  textDiff: (path: string, content: string) =>
    fetch(apiUrl("/api/v1/git/text-diff"), {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ path, content }),
    }).then((r) => r.json()) as Promise<{ has_changes: boolean; lines: Array<{ type: string; text: string }> }>,
};

// WebSocket helper — includes auth token as query param
export function wsUrl(instanceId: number): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  const base =
    configured ||
    (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000");
  const wsBase = base.replace(/^http/, "ws");
  const token = useAuthStore.getState().token ?? "";
  return `${wsBase}/ws/terminal/${instanceId}?token=${encodeURIComponent(token)}`;
}