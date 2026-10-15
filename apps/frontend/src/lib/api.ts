export type HealthResponse = {
  status: "ok";
};

export type AuthSession = {
  authenticated: boolean;
  username: string | null;
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
  batch_id?: number | null;
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

export type ExecutionArtifact = {id: number; execution_automation_id: number; filename: string; size: number; checksum: string};

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
  profile_credentials?: Record<string, {username: string; password: string}>;
};

export type BatchFlowInput = {automation_id: number; version: number; inputs: Record<string, unknown>; test_mode: boolean};
export type ExecutionBatch = {id: number; name: string; status: string; created_at: string; executions: Execution[]};
export type CreateBatchInput = {name: string; idempotency_key: string; items: BatchFlowInput[]; profile_credentials?: Record<string, {username: string; password: string}>};

export type Destination = {
  id: number;
  code: string;
  name: string;
  path_reference: string;
  enabled: boolean;
  last_test_status: string | null;
  last_test_at: string | null;
};

export type DestinationListResponse = {
  items: Destination[];
  total: number;
  limit: number;
  offset: number;
};

export type CreateDestinationInput = {
  code: string;
  name: string;
  path_reference: string;
  enabled?: boolean;
};

export type CreateAutomationInput = {
  code: string;
  name: string;
  description?: string;
  system?: string;
};

export type AutomationVersion = {
  id: number;
  automation_id: number;
  version: number;
  recipe: Record<string, unknown>;
  created_at: string;
  created_by: string | null;
  test_status: string | null;
  published: boolean;
  published_at: string | null;
};

export type AutomationVersionTestResponse = {
  version: number;
  test_status: string;
  automation_status: string;
};

export type AutomationVersionPublishResponse = {
  version: number;
  published: boolean;
  automation_status: string;
};

export type LoginTarget = {selector: string; frames: string[]};
export type LoginConfiguration = {
  login_url: string; allowed_origins: string[];
  username_target: LoginTarget | null; password_target: LoginTarget | null; submit_target: LoginTarget | null;
  success_rule: {kind: "marker" | "url"; target?: LoginTarget | null; url?: string | null} | null;
};
export type SiteLoginProfile = {id: number; name: string; group_id?: number | null; group_name?: string | null; status: string; current_version: number; configuration: LoginConfiguration; published: boolean};
export type AccessGroup = {id: number; name: string};
export type Routine = {id: number; name: string; items: {automation_id: number; version: number; inputs: Record<string, unknown>}[]};
export type LoginRecording = {id: string; profile_id: number; version: number; status: string; targets: Partial<Record<"username_target" | "password_target" | "submit_target", LoginTarget>>; error: string | null};
export type FlowRecording = {id: string; phase?: "PREPARING" | "RECORDING"; status: string; recipe: Record<string, unknown> | null; error: string | null};
export type TargetKind = 'element' | 'text' | 'select' | 'checkbox' | 'range' | 'color';
export type TargetPicking = {id: string; status: 'RECORDING' | 'DONE' | 'FAILED' | 'CANCELLED'; phase: 'PREPARING' | 'SELECTING'; target: {selector: string} | null; error: string | null};

export type ReportOptionsResponse = {
  fields: Record<string, {options: {value: string; label: string; disabled: boolean}[]; error: string | null}>;
};

export type DiagnosticsResponse = {
  status: string;
  database: { status: string };
  workers: { online: number; total: number };
  authentication: { configured: number; renewal_configured: number };
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
  import.meta.env.VITE_API_URL ?? (window.location.hostname === "localhost" ? "http://localhost:8000" : "http://127.0.0.1:8000");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    if (payload && typeof payload === "object" && "error" in payload) {
      const error = payload.error;
      if (error && typeof error === "object" && "message" in error && typeof error.message === "string" && error.message.trim()) {
        throw new Error(error.message);
      }
    }
    throw new Error(`API_REQUEST_FAILED:${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  listExecutionArtifacts: (executionId: number) => request<{items: ExecutionArtifact[]}>(`/executions/${executionId}/artifacts`),
  downloadExecutionArtifact: async (executionId: number, artifactId: number): Promise<Blob> => {
    const response = await fetch(`${API_BASE_URL}/executions/${executionId}/artifacts/${artifactId}/download`, {credentials: 'include', cache: 'no-store'});
    if (!response.ok) throw new Error('ARTIFACT_UNAVAILABLE');
    return response.blob();
  },
  getAuthSession: () => request<AuthSession>("/auth/session"),
  requestPairingCode: () => request<{issued: boolean; expires_in: number}>("/auth/pairing-code", {method: "POST"}),
  login: (pairingCode: string) =>
    request<AuthSession>("/auth/login", { method: "POST", body: JSON.stringify({ pairing_code: pairingCode }) }),
  logout: () => request<AuthSession>("/auth/logout", { method: "POST" }),
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

  deleteAutomation: (id: number) => request<{archived: boolean}>(`/automations/${id}`, {method: "DELETE"}),

  createAutomation: (input: CreateAutomationInput) =>
    request<Automation>("/automations", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  createAutomationVersion: (
    automationId: number,
    recipe: Record<string, unknown>,
    createdBy = "studio",
  ) =>
    request<AutomationVersion>(`/automations/${automationId}/versions`, {
      method: "POST",
      body: JSON.stringify({ recipe, created_by: createdBy }),
    }),

  getAutomationVersion: (automationId: number, version: number) =>
    request<AutomationVersion>(`/automations/${automationId}/versions/${version}`),

  listLoginProfiles: () => request<{items: SiteLoginProfile[]; total: number; limit: number; offset: number}>("/login-profiles"),
  getLoginProfileVersion: (id: number, version: number) => request<SiteLoginProfile>(`/login-profiles/${id}/versions/${version}`),
  createLoginProfile: (input: {name: string; login_url: string; group_id?: number; template_profile_id?: number}) => request<SiteLoginProfile>("/login-profiles", {method: "POST", body: JSON.stringify(input)}),
  listAccessGroups: () => request<{items: AccessGroup[]}>("/access-groups"),
  createAccessGroup: (name: string) => request<AccessGroup>("/access-groups", {method: "POST", body: JSON.stringify({name})}),
  deleteAccessGroup: (id: number) => request<void>(`/access-groups/${id}`, {method: "DELETE"}),
  setAccessGroup: (id: number, group_id: number | null) => request<SiteLoginProfile>(`/login-profiles/${id}/group`, {method: "PUT", body: JSON.stringify({group_id})}),
  listRoutines: () => request<{items: Routine[]}>("/routines"),
  startFlowRecording: (url: string) => request<FlowRecording>("/flow-recordings", {method: "POST", body: JSON.stringify({url})}),
  startTargetPicking: (url: string, kind: TargetKind) => request<TargetPicking>('/target-pickings', {method: 'POST', body: JSON.stringify({url, kind})}),
  getTargetPicking: (id: string, signal?: AbortSignal) => request<TargetPicking>(`/target-pickings/${id}`, {signal}),
  cancelTargetPicking: (id: string) => request<TargetPicking>(`/target-pickings/${id}/cancel`, {method: 'POST'}),
  getFlowRecording: (id: string) => request<FlowRecording>(`/flow-recordings/${id}`),
  finishFlowRecording: (id: string) => request<FlowRecording>(`/flow-recordings/${id}/finish`, {method: "POST"}),
  cancelFlowRecording: (id: string) => request<FlowRecording>(`/flow-recordings/${id}/cancel`, {method: "POST"}),
  getRoutine: (id: number) => request<Routine>(`/routines/${id}`),
  saveRoutine: (input: Omit<Routine, "id">) => request<Routine>("/routines", {method: "POST", body: JSON.stringify(input)}),
  deleteRoutine: (id: number) => request<void>(`/routines/${id}`, {method: "DELETE"}),
  createLoginProfileVersion: (id: number, configuration: LoginConfiguration) => request<SiteLoginProfile>(`/login-profiles/${id}/versions`, {method: "POST", body: JSON.stringify(configuration)}),
  publishLoginProfile: (id: number, version: number) => request<SiteLoginProfile>(`/login-profiles/${id}/publish`, {method: "POST", body: JSON.stringify({version})}),
  deleteLoginProfile: (id: number) => request<void>(`/login-profiles/${id}/permanent`, {method: "DELETE"}),
  disableLoginProfile: (id: number) => request<SiteLoginProfile>(`/login-profiles/${id}`, {method: "DELETE"}),
  startLoginRecording: (id: number) => request<LoginRecording>(`/login-profiles/${id}/recordings`, {method: "POST"}),
  getLoginRecording: (id: number, recordingId: string) => request<LoginRecording>(`/login-profiles/${id}/recordings/${recordingId}`),
  cancelLoginRecording: (id: number, recordingId: string) => request<LoginRecording>(`/login-profiles/${id}/recordings/${recordingId}/cancel`, {method: "POST"}),
  getReportOptions: (automationId: number, version: number, inputs: Record<string, unknown>, profileCredentials?: Record<string, {username: string; password: string}>) =>
    request<ReportOptionsResponse>(`/automations/${automationId}/versions/${version}/input-options`, {
      method: "POST", body: JSON.stringify({inputs, ...(profileCredentials ? {profile_credentials: profileCredentials} : {})}),
    }),

  testAutomationVersion: (automationId: number, version: number) =>
    request<AutomationVersionTestResponse>(
      `/automations/${automationId}/versions/${version}/test`,
      { method: "POST" },
    ),

  publishAutomationVersion: (automationId: number, version: number) =>
    request<AutomationVersionPublishResponse>(
      `/automations/${automationId}/versions/${version}/publish`,
      { method: "POST" },
    ),

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
  createBatch: (input: CreateBatchInput) => request<ExecutionBatch>("/execution-batches", {method: "POST", body: JSON.stringify(input)}),
  getBatch: (id: number) => request<ExecutionBatch>(`/execution-batches/${id}`),
  listBatches: () => request<{items: ExecutionBatch[]; total: number}>("/execution-batches"),
  cancelBatch: (id: number) => request<ExecutionBatch>(`/execution-batches/${id}/cancel`, {method: "POST"}),
  deleteBatch: (id: number) => request<void>(`/execution-batches/${id}`, {method: "DELETE"}),

  createExecution: (input: CreateExecutionInput) =>
    request<Execution>("/executions", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  deleteExecution: (id: number) => request<void>(`/executions/${id}`, {method: "DELETE"}),
  cancelExecution: (id: number) =>
    request<Execution>(`/executions/${id}/cancel`, {
      method: "POST",
    }),

  getDiagnostics: () => request<DiagnosticsResponse>("/diagnostics"),

  listDestinations: (params?: { limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.limit != null) query.set("limit", String(params.limit));
    if (params?.offset != null) query.set("offset", String(params.offset));

    const suffix = query.toString() ? "?" + query.toString() : "";
    return request<DestinationListResponse>(`/destinations${suffix}`);
  },

  createDestination: (input: CreateDestinationInput) =>
    request<Destination>("/destinations", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateDestination: (id: number, input: CreateDestinationInput) =>
    request<Destination>(`/destinations/${id}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),

  deleteDestination: (id: number) =>
    request<void>(`/destinations/${id}`, {
      method: "DELETE",
    }),
};

export function executionEventsUrl(id: number) {
  return new URL(`/executions/${id}/events`, API_BASE_URL).toString();
}
