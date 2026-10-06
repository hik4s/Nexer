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

const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
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
};
