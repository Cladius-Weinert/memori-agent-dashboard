export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface UserTeam {
  user_id: number;
  team_id: number;
  role: string;
}

export interface Team {
  id: number;
  name: string;
  members: UserTeam[];
}

export interface Provider {
  id: number;
  team_id: number;
  type: string;
  name: string;
  credentials_ref: string | null;
  created_at: string;
}

export interface Instance {
  id: number;
  team_id: number;
  provider_id: number | null;
  name: string;
  host: string;
  port: number;
  ssh_user: string;
  status: string;
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  last_checked_at: string | null;
}

export interface CommandResult {
  exit_code: number;
  stdout: string;
  stderr: string;
}

export interface AgentJob {
  id: number;
  user_id: number;
  goal: string;
  plan: unknown[];
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface AgentAction {
  id: number;
  job_id: number;
  tool: string;
  params: Record<string, unknown>;
  result: Record<string, unknown>;
  requires_approval: boolean;
  approved_by: number | null;
  created_at: string;
}

export interface MetricPoint {
  ts: string;
  value: number;
}

export interface Metrics {
  cpu: MetricPoint[];
  ram: MetricPoint[];
  disk: MetricPoint[];
}