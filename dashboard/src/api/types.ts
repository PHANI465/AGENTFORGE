export type AgentStatus = "draft" | "active" | "archived"
export type RunStatus = "pending" | "running" | "completed" | "failed"
export type RunStepType = "llm_call" | "tool_call" | "safety_check"
export type EvalRunStatus = "pending" | "running" | "completed" | "failed"
export type SafetyViolationAction = "block" | "warn" | "log"

export interface ToolSpec {
  name: string
  description: string
  parameters_schema: Record<string, unknown>
}

export interface SafetyPolicy {
  rules: string[]
  on_violation: SafetyViolationAction
}

export interface TokenOptimizationConfig {
  enable_caching: boolean
  enable_smart_routing: boolean
  simple_model: string | null
  complex_model: string | null
  complexity_threshold: number
  enable_compression: boolean
  compression_threshold_chars: number
  daily_budget_usd: number | null
}

export interface AgentConfig {
  max_tokens: number
  temperature: number
  timeout: number
  retry_policy: Record<string, unknown> | null
  optimization: TokenOptimizationConfig
}

export interface Agent {
  id: string
  name: string
  model: string
  system_prompt: string
  tools: ToolSpec[]
  safety_policy: SafetyPolicy
  config: AgentConfig
  status: AgentStatus
  created_at: string
  updated_at: string
}

export interface AgentCreate {
  name: string
  model: string
  system_prompt: string
  tools?: ToolSpec[]
  safety_policy?: SafetyPolicy
  config?: Partial<AgentConfig>
}

export interface AgentUpdate {
  name?: string
  model?: string
  system_prompt?: string
  tools?: ToolSpec[]
  safety_policy?: SafetyPolicy
  config?: Partial<AgentConfig>
  status?: AgentStatus
}

export interface Run {
  id: string
  agent_id: string
  agent_version: number
  input: string
  output: string | null
  status: RunStatus
  trace_id: string | null
  started_at: string | null
  completed_at: string | null
}

export interface TraceSpan {
  step_number: number
  type: RunStepType
  input: Record<string, unknown>
  output: Record<string, unknown>
  tokens_in: number | null
  tokens_out: number | null
  latency_ms: number | null
}

export interface TraceSummary {
  total_steps: number
  total_llm_calls: number
  total_tool_calls: number
  total_safety_checks: number
  total_tokens_in: number
  total_tokens_out: number
  total_latency_ms: number
}

export interface TraceResponse {
  run_id: string
  agent_id: string
  trace_id: string | null
  status: RunStatus
  input: string
  output: string | null
  spans: TraceSpan[]
  summary: TraceSummary
}

export interface EvalTestCase {
  id?: string | null
  input: string
  expected_output?: string | null
  expected_tool_calls?: string[]
  tags?: string[]
}

export interface EvalSuite {
  id: string
  name: string
  agent_id: string
  test_cases: EvalTestCase[]
  created_at: string
}

export interface EvalResultOut {
  test_case_id: string
  passed: boolean
  score: number | null
  actual_output: string | null
  latency_ms: number | null
  tokens_used: number | null
  safety_violations: Record<string, unknown>[]
}

export interface EvalRunSummary {
  total: number
  passed: number
  failed: number
  pass_rate: number
  avg_latency_ms: number
  total_cost_usd: number
  total_tokens_used: number
}

export interface EvalRunOut {
  id: string
  suite_id: string
  agent_version: number
  status: EvalRunStatus
  summary: EvalRunSummary | null
  started_at: string | null
  completed_at: string | null
  results: EvalResultOut[]
}

export interface EvalCompareOut {
  run_a: EvalRunOut
  run_b: EvalRunOut
  pass_rate_delta: number | null
  avg_latency_ms_delta: number | null
  total_cost_usd_delta: number | null
}

export interface CostBreakdownRow {
  date: string
  agent_id: string
  total_cost_usd: number
  total_tokens_in: number
  total_tokens_out: number
  call_count: number
}

export interface UsageSummary {
  window_days: number
  total_calls: number
  total_cost_usd: number
  total_tokens_in: number
  total_tokens_out: number
  avg_cost_per_call_usd: number
}

export interface ApiKeyOut {
  id: string
  user_id: string
  provider: string
  created_at: string
}

export interface ApiKeyCreated extends ApiKeyOut {
  raw_key: string
}

export interface DataResponse<T> {
  data: T
  meta: Record<string, unknown> | null
}

export interface ListMeta {
  next_cursor: string | null
  limit: number
}

export interface ListResponse<T> {
  data: T[]
  meta: ListMeta
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
  }
}
