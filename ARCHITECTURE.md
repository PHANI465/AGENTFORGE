# AgentForge — Architecture Document

---

## System Overview

AgentForge is composed of 6 core components that work together to provide the full agent lifecycle:

```
User Request → API Gateway → Agent Runtime → LLM Proxy (LiteLLM) → LLM Provider
                                  │
                            ┌─────┴──────┐
                            │             │
                       Eval Pipeline   Trace Collector
                            │             │
                            └──────┬──────┘
                                   │
                              Dashboard
```

---

## Component Details

### 1. Python SDK (`packages/sdk/`)

The developer-facing interface. Users define agents, tools, and safety policies in Python.

**Responsibilities:**
- Agent definition (model, tools, system prompt, safety rules)
- Tool registration with type-safe schemas
- Safety policy definition
- CLI commands (`agentforge deploy`, `agentforge eval`, `agentforge logs`)
- Client library for programmatic access

**Key Models:**
```python
Agent(name, model, tools, system_prompt, safety_policy, config)
Tool(name, description, function, parameters_schema)
SafetyPolicy(rules: list[str], on_violation: "block" | "warn" | "log")
AgentConfig(max_tokens, temperature, timeout, retry_policy)
```

**Depends on:** API Gateway (HTTP client)

---

### 2. API Gateway (`services/api-gateway/`)

The single entry point for all platform interactions. FastAPI application.

**Responsibilities:**
- REST API for CRUD operations on agents, tools, policies
- Authentication and authorization (API keys, JWT)
- Rate limiting
- Request validation
- Routes agent execution requests to the Agent Runtime
- Serves the Dashboard's API needs

**Key Endpoints:**
```
POST   /api/v1/agents              — Register a new agent
GET    /api/v1/agents              — List agents
GET    /api/v1/agents/{id}         — Get agent details
PUT    /api/v1/agents/{id}         — Update agent
DELETE /api/v1/agents/{id}         — Delete agent
POST   /api/v1/agents/{id}/run     — Execute an agent (send a message)
GET    /api/v1/agents/{id}/runs    — List past runs
GET    /api/v1/runs/{id}/trace     — Get full execution trace

POST   /api/v1/evals               — Create an evaluation run
GET    /api/v1/evals/{id}          — Get eval results
GET    /api/v1/evals/{id}/compare  — Compare two eval runs

GET    /api/v1/analytics/costs     — Cost breakdown by agent/day
GET    /api/v1/analytics/usage     — Token usage analytics
GET    /api/v1/analytics/health    — System health metrics
```

**Depends on:** PostgreSQL, Agent Runtime, Eval Service

---

### 3. Agent Runtime (`services/agent-runtime/`)

The brain of the platform. Executes agents through their reasoning-action loop.

**Responsibilities:**
- Agent execution loop (think → decide → act → observe → repeat)
- Tool orchestration (call external functions, handle results)
- Safety policy enforcement (check every action against rules before execution)
- Context management (conversation history, tool results)
- Streaming responses

**Execution Flow:**
```
1. Receive request (user message + agent config)
2. Build context (system prompt + history + user message)
3. [Optional] Compress context via LLMLingua
4. Send to LLM via LiteLLM
5. LLM responds with either:
   a. Final answer → return to user
   b. Tool call → execute tool → add result to context → go to step 4
6. Before each tool execution, check safety policies
7. Emit trace events at every step (OpenTelemetry)
8. Track token usage for cost calculation
```

**Key Design:**
- Max iterations per run (default: 10) to prevent infinite loops
- Tool execution timeout (default: 30s)
- Safety check is a middleware — runs before every tool call
- All state is in-memory per request (stateless service)

**Depends on:** LiteLLM, OpenTelemetry, PostgreSQL (for agent configs)

---

### 4. Token Optimization Layer

Not a separate service — it's the LiteLLM instance + optional compression middleware.

**Components:**

**LiteLLM (deployed as a sidecar or standalone service):**
- Smart routing: simple prompts → GPT-4o-mini, complex → GPT-4o
- Response caching: Redis-backed, exact + semantic match
- Cost tracking: tokens × public pricing, per-user/per-agent
- Budget limits: per API key, per agent, per day
- Provider abstraction: swap models without code changes

**LLMLingua (integrated into Agent Runtime, optional):**
- Prompt compression before LLM calls
- Configurable per agent (some agents need full context)
- Best for agents with large knowledge bases or long conversations

---

### 5. Evaluation Pipeline (`services/eval-service/`)

Automated testing for AI agents. Run test suites, score results, compare versions.

**Responsibilities:**
- Define test cases (input + expected behavior)
- Run agents against test suites
- Score results (accuracy, latency, cost, safety violations)
- Compare versions side-by-side (v1 vs v2)
- Store eval history for trend analysis

**Key Models:**
```python
EvalSuite(name, agent_id, test_cases: list[TestCase])
TestCase(input, expected_output, expected_tool_calls, tags)
EvalRun(suite_id, agent_version, results: list[EvalResult])
EvalResult(test_case_id, actual_output, score, latency_ms, tokens_used, safety_violations)
```

**Scoring:**
- **Accuracy**: LLM-as-judge (does the output match expected behavior?)
- **Tool correctness**: Did the agent call the right tools with right params?
- **Latency**: p50, p95, p99
- **Cost**: Total tokens × price
- **Safety**: Number of policy violations

**Depends on:** Agent Runtime (to execute agents), PostgreSQL (store results)

---

### 6. Observability Stack

**Trace Collector (`services/trace-collector/`):**
- Receives OpenTelemetry spans from Agent Runtime
- Stores traces in PostgreSQL (for MVP; move to ClickHouse/Jaeger later)
- Provides trace query API for the dashboard

**Prometheus:**
- Scrapes metrics from all services
- Key metrics: request_count, latency_histogram, tokens_used, cost_total, safety_violations, active_agents

**Grafana:**
- Pre-built dashboards for agent health, costs, safety
- Alerting rules (e.g., "safety violations > 3 in 5 min")

---

### 7. Dashboard (`dashboard/`)

React + TypeScript web UI for the platform.

**Pages:**
- **Agent Catalog**: List all agents, their status, quick stats
- **Agent Detail**: Config, recent runs, cost, safety summary
- **Trace Viewer**: Click any run → see full reasoning chain, tool calls, timing
- **Eval Results**: Test suite results, version comparison charts
- **Cost Analytics**: Per-agent, per-day cost breakdown, budget alerts
- **Settings**: API keys, safety policies, notification preferences

---

## Data Model (PostgreSQL)

```
agents
  id, name, model, system_prompt, tools_config, safety_policy, config, status, created_at, updated_at

agent_versions
  id, agent_id, version, snapshot (full config at this version), created_at

api_keys
  id, key_hash, user_id, provider, encrypted_key, created_at

runs
  id, agent_id, agent_version, input, output, status, started_at, completed_at

run_steps
  id, run_id, step_number, type (llm_call | tool_call | safety_check), input, output, tokens_in, tokens_out, latency_ms, created_at

eval_suites
  id, name, agent_id, test_cases (jsonb), created_at

eval_runs
  id, suite_id, agent_version, status, summary (jsonb), started_at, completed_at

eval_results
  id, eval_run_id, test_case_id, passed, score, actual_output, latency_ms, tokens_used, safety_violations, created_at

cost_records
  id, agent_id, run_id, model, tokens_in, tokens_out, cost_usd, created_at
```

---

## Service Communication

- **Sync (HTTP)**: API Gateway ↔ Agent Runtime, API Gateway ↔ Eval Service
- **Async (Redis Pub/Sub)**: Agent Runtime → Trace Collector (emit spans), Eval Service → Agent Runtime (run agent for eval)
- **Direct**: All services → PostgreSQL, Agent Runtime → LiteLLM → LLM Provider

---

## Security Considerations

This section describes the original design intent. **See
[`docs/security.md`](docs/security.md) for what's actually implemented**,
including an honest list of gaps (e.g. BYOK keys are not currently encrypted
at rest, despite the intent below) — that document supersedes this one.

- API keys stored encrypted at rest (AES-256 via Fernet)
- User LLM keys never logged, never included in traces
- Safety policy checks run in-process (not bypassable)
- All API endpoints require authentication
- Rate limiting at gateway level
- CORS configured for dashboard origin only

---

## Local Development Setup

See [`README.md`](README.md) for the current, accurate setup instructions and
port table — the dashboard ended up on `3001` and Grafana on `3000` (the
reverse of this doc's original plan), since Grafana claimed `3000` in
Milestone 5 before the dashboard existed in Milestone 8.
