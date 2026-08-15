import type {
  Agent,
  AgentCreate,
  AgentUpdate,
  ApiErrorBody,
  ApiKeyCreated,
  ApiKeyOut,
  DataResponse,
  EvalCompareOut,
  EvalRunOut,
  EvalSuite,
  EvalTestCase,
  ListResponse,
  Run,
  TraceResponse,
  CostBreakdownRow,
  UsageSummary,
} from "./types"

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
const STORAGE_KEY = "agentforge.api_key"

export class ApiError extends Error {
  code: string
  status: number
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export function getApiKey(): string | null {
  return localStorage.getItem(STORAGE_KEY)
}

export function setApiKey(key: string) {
  localStorage.setItem(STORAGE_KEY, key)
}

export function clearApiKey() {
  localStorage.removeItem(STORAGE_KEY)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiKey = getApiKey()
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
      ...(init?.headers ?? {}),
    },
  })

  if (res.status === 204) {
    return undefined as T
  }

  const body = await res.json().catch(() => null)

  if (!res.ok) {
    const errBody = body as ApiErrorBody | null
    throw new ApiError(
      res.status,
      errBody?.error?.code ?? "unknown_error",
      errBody?.error?.message ?? `Request failed with status ${res.status}`,
    )
  }

  return body as T
}

// --- Agents ---

export const agentsApi = {
  list: (opts?: { status?: string; search?: string }) => {
    const params = new URLSearchParams({ limit: "100" })
    if (opts?.status) params.set("status", opts.status)
    if (opts?.search) params.set("search", opts.search)
    return request<ListResponse<Agent>>(`/api/v1/agents?${params.toString()}`)
  },
  get: (id: string) => request<DataResponse<Agent>>(`/api/v1/agents/${id}`),
  create: (payload: AgentCreate) =>
    request<DataResponse<Agent>>("/api/v1/agents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: string, payload: AgentUpdate) =>
    request<DataResponse<Agent>>(`/api/v1/agents/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  delete: (id: string) =>
    request<void>(`/api/v1/agents/${id}`, { method: "DELETE" }),
  clone: (id: string, name?: string) =>
    request<DataResponse<Agent>>(`/api/v1/agents/${id}/clone`, {
      method: "POST",
      body: JSON.stringify(name ? { name } : {}),
    }),
}

// --- Runs ---

export const runsApi = {
  run: (agentId: string, input: string) =>
    request<DataResponse<Run>>(`/api/v1/agents/${agentId}/run`, {
      method: "POST",
      body: JSON.stringify({ input }),
    }),
  listForAgent: (agentId: string, limit = 20) =>
    request<ListResponse<Run>>(`/api/v1/agents/${agentId}/runs?limit=${limit}`),
  trace: (runId: string) =>
    request<DataResponse<TraceResponse>>(`/api/v1/runs/${runId}/trace`),
}

// --- Evals ---

export const evalsApi = {
  listSuites: () => request<ListResponse<EvalSuite>>("/api/v1/eval-suites?limit=100"),
  getSuite: (id: string) => request<DataResponse<EvalSuite>>(`/api/v1/eval-suites/${id}`),
  createSuite: (payload: { name: string; agent_id: string; test_cases: EvalTestCase[] }) =>
    request<DataResponse<EvalSuite>>("/api/v1/eval-suites", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runSuite: (suiteId: string) =>
    request<DataResponse<EvalRunOut>>(`/api/v1/eval-suites/${suiteId}/run`, {
      method: "POST",
    }),
  listRuns: (suiteId: string) =>
    request<ListResponse<EvalRunOut>>(`/api/v1/eval-suites/${suiteId}/runs`),
  getRun: (runId: string) => request<DataResponse<EvalRunOut>>(`/api/v1/eval-runs/${runId}`),
  compare: (runA: string, runB: string) =>
    request<DataResponse<EvalCompareOut>>(`/api/v1/eval-runs/${runA}/compare/${runB}`),
}

// --- Analytics ---

export const analyticsApi = {
  usage: (days = 7, agentId?: string) =>
    request<DataResponse<UsageSummary>>(
      `/api/v1/analytics/usage?days=${days}${agentId ? `&agent_id=${agentId}` : ""}`,
    ),
  costs: (days = 7, agentId?: string) =>
    request<DataResponse<CostBreakdownRow[]>>(
      `/api/v1/analytics/costs?days=${days}${agentId ? `&agent_id=${agentId}` : ""}`,
    ),
}

// --- API Keys ---

export const apiKeysApi = {
  list: () => request<ListResponse<ApiKeyOut>>("/api/v1/api-keys"),
  create: (userId: string, provider = "openai") =>
    request<DataResponse<ApiKeyCreated>>("/api/v1/api-keys", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, provider }),
    }),
  delete: (id: string) =>
    request<void>(`/api/v1/api-keys/${id}`, { method: "DELETE" }),
}
