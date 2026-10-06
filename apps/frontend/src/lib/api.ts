export type HealthResponse = {
  status: "ok";
};

export type Automation = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  system: string | null;
  status: string;
  current_version: number | null;
};

export type AutomationListResponse = {
  items: Automation[];
  total: number;
  limit: number;
  offset: number;
};

export type ExecutionItem = {
  id: number;
  execution_id: number;
  automation_id: number;
  automation_version: number;
  status: string;
  stage: string;
  attempts: number;
  last_progress_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_type: string | null;
  error_detail: string | null;
};

export type Execution = {
  id: number;
  name: string;
  requested_by: string | null;
  period_start: string | null;
  period_end: string | null;
  status: string;
  send_to_network: boolean;
  keep_local_copy: boolean;
  overwrite_existing: boolean;
  test_mode: boolean;
  inputs: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  cancel_requested: boolean;
  items: ExecutionItem[];
};

export type ExecutionListResponse = {
  items: Execution[];
  total: number;
  limit: number;
  offset: number;
};

export type CreateExecutionInput = {
  name: string;
  automation_ids: number[];
  period_start?: string;
  period_end?: string;
  send_to_network?: boolean;
  keep_local_copy?: boolean;
  overwrite_existing?: boolean;
  test_mode?: boolean;
  inputs?: Record<string, unknown>;
};

export type DiagnosticsResponse = {
  status: string;
  database: { status: string };
  workers: { online: number; total: number };
};

export type ExecutionEvent = {
  id: number;
  type: string;
  level: string;
  message: string;
  payload: Record<string, unknown> | null;
  created_at: string;
};

const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`API_REQUEST_FAILED:${response.status}`);
  }

  return (await response.json()) as T;
}

export const api = {
  getHealth: () => request<HealthResponse>("/health"),

  listAutomations: (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();

    if (params?.status) query.set("status", params.status);
    if (params?.limit != null) query.set("limit", String(params.limit));
    if (params?.offset != null) query.set("offset", String(params.offset));

    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<AutomationListResponse>(`/automations${suffix}`);
  },

  listExecutions: (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();

    if (params?.status) query.set("status", params.status);
    if (params?.limit != null) query.set("limit", String(params.limit));
    if (params?.offset != null) query.set("offset", String(params.offset));

    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<ExecutionListResponse>(`/executions${suffix}`);
  },

  getExecution: (id: number) => request<Execution>(`/executions/${id}`),

  createExecution: (input: CreateExecutionInput) =>
    request<Execution>("/executions", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  cancelExecution: (id: number) =>
    request<Execution>(`/executions/${id}/cancel`, {
      method: "POST",
    }),

  getDiagnostics: () => request<DiagnosticsResponse>("/diagnostics"),
};

export function executionEventsUrl(id: number) {
  return new URL(`/executions/${id}/events`, API_BASE_URL).toString();
}
