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
const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL ?? "http://localhost:8004"
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
  // llmApiKey (BYOK): when provided, it's encrypted server-side and stored
  // on the new key; every agent run authenticated with that key then uses
  // it instead of the platform's shared key.
  create: (userId: string, provider = "openai", llmApiKey = "") =>
    request<DataResponse<ApiKeyCreated>>("/api/v1/api-keys", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, provider, llm_api_key: llmApiKey }),
    }),
  delete: (id: string) =>
    request<void>(`/api/v1/api-keys/${id}`, { method: "DELETE" }),
}

// --- Knowledge base (RAG) ---
export interface KnowledgeInfo {
  chunk_count: number
  sources: string[]
}

export const knowledgeApi = {
  get: (agentId: string) =>
    request<DataResponse<KnowledgeInfo>>(`/api/v1/agents/${agentId}/knowledge`),
  add: (agentId: string, source: string, text: string) =>
    request<DataResponse<KnowledgeInfo>>(`/api/v1/agents/${agentId}/knowledge`, {
      method: "POST",
      body: JSON.stringify({ source, text }),
    }),
  clear: (agentId: string) =>
    request<void>(`/api/v1/agents/${agentId}/knowledge`, { method: "DELETE" }),
}

// --- Demo ---
//
// Only a public-demo deployment answers this (api-gateway returns 404
// otherwise). Lets the sign-in page offer one-click entry with the shared
// demo key instead of making a visitor hunt for it. Returns null on any
// failure so a normal deployment simply shows no demo button.
export const demoApi = {
  async getKey(): Promise<string | null> {
    try {
      const res = await request<DataResponse<{ api_key: string }>>("/api/v1/demo/api-key")
      return res.data.api_key || null
    } catch {
      return null
    }
  },
}

// --- Identity (services/auth-service — Phase 3.3) ---
//
// Two-step login: auth-service proves who you are and hands back a JWT;
// that JWT is then exchanged for a real AgentForge API key via
// api-gateway's bootstrap endpoint (POST /api/v1/api-keys/bootstrap),
// which is what actually gets stored and used for every other request.
// Every other page in this app only ever sees the API key — this is the
// only file that touches a JWT at all, and only transiently, in memory.

interface AuthTokens {
  access_token: string
  refresh_token: string
}

/** Same envelope-parsing/error-throwing shape as the main request()
 * helper above, but for the two auth calls that don't go through
 * api-gateway with an X-API-Key — auth-service itself, and the
 * bootstrap call's Bearer-token auth. */
async function rawEnvelopeFetch<T>(url: string, init: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  const parsed = await res.json().catch(() => null)
  if (!res.ok) {
    const errBody = parsed as ApiErrorBody | null
    throw new ApiError(
      res.status,
      errBody?.error?.code ?? "unknown_error",
      errBody?.error?.message ?? `Request failed with status ${res.status}`,
    )
  }
  return (parsed as { data: T }).data
}

async function bootstrapApiKeyFromToken(accessToken: string): Promise<string> {
  const created = await rawEnvelopeFetch<ApiKeyCreated>(`${BASE_URL}/api/v1/api-keys/bootstrap`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return created.raw_key
}

export const identityApi = {
  /** Email+password signup, then immediately exchanges the resulting JWT
   * for a real API key. Returns the API key — callers still call
   * setApiKey() themselves, same as every other sign-in path, so there's
   * one single place that decides what "signed in" means. */
  signup: async (email: string, password: string): Promise<string> => {
    const tokens = await rawEnvelopeFetch<AuthTokens>(`${AUTH_SERVICE_URL}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })
    return bootstrapApiKeyFromToken(tokens.access_token)
  },
  login: async (email: string, password: string): Promise<string> => {
    const tokens = await rawEnvelopeFetch<AuthTokens>(`${AUTH_SERVICE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })
    return bootstrapApiKeyFromToken(tokens.access_token)
  },
  /** Used by the /auth/callback page after an OAuth provider redirects
   * back with tokens already in hand (in the URL fragment, not a fetch
   * response) — same bootstrap step, just a different way of getting the
   * initial access token. */
  bootstrapFromAccessToken: bootstrapApiKeyFromToken,
  oauthLoginUrl: (provider: "github" | "google") => `${AUTH_SERVICE_URL}/auth/oauth/${provider}/login`,
}
