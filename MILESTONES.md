# AgentForge — Milestones

> One step at a time. Each milestone has a clear deliverable.
> After completing each milestone, report: what's done, what's next, what to do in Cursor.

---

## Milestone 0: Project Scaffolding ✅ DONE
**Goal**: Empty but runnable project structure with all services stubbed.

**Deliverables:**
- [x] Monorepo structure (all directories from CLAUDE.md project structure)
- [x] `pyproject.toml` with workspace config (uv workspace, 4 services + 2 packages)
- [x] Stub `__init__.py` and `main.py` for each service
- [x] `docker-compose.yml` with all services (FastAPI apps return health check) — `infra/docker/docker-compose.yml`
- [x] `Dockerfile` for each service
- [x] `.env.example` with all required environment variables
- [x] `.gitignore`
- [x] `README.md` (project overview, setup instructions)
- [x] All services start with `docker-compose up` and respond to `GET /health` — verified 2026-08-10

**Done when**: `docker-compose up` starts all services, `curl localhost:8000/health` returns `{"status": "ok"}`. ✅ **Milestone 0 fully complete.**

**Verification status**: `uv sync --all-packages` resolves and installs the full workspace cleanly. `docker compose -f infra/docker/docker-compose.yml --env-file .env up -d` started all services; `api-gateway` (8000), `agent-runtime` (8001), `eval-service` (8002), and `trace-collector` (8003) all responded `{"status": "ok"}` on `/health`.

---

## Milestone 1: Shared Models & Database ✅ DONE (2026-08-10)
**Goal**: Define all Pydantic models and set up PostgreSQL with Alembic migrations.

**Deliverables:**
- [x] `packages/common/` — shared Pydantic models (Agent, Tool, SafetyPolicy, Run, EvalSuite, etc.) — `agentforge_common/models.py` + `enums.py`
- [x] PostgreSQL connection setup with SQLAlchemy async — `agentforge_common/db.py`
- [x] Alembic migration for initial schema (all tables from ARCHITECTURE.md) — `packages/common/alembic/versions/0001_initial_schema.py`, all 9 tables
- [x] Database seed script with sample data — `scripts/seed.py`
- [x] Unit tests for models — `tests/unit/common/test_models.py`, 9/9 passing

**Done when**: Migrations run, seed data is in the database, models validate correctly. ✅ **Fully verified against the live Postgres container.**

**Verification status**: `alembic upgrade head` created all 9 tables + 4 Postgres enum types; `alembic downgrade base` → `upgrade head` round-tripped cleanly. `scripts/seed.py` inserted 1 agent, 1 run, 3 run steps, 1 cost record, 1 eval suite, 1 eval run, 2 eval results — row counts confirmed via direct query. `pytest` 9/9 passed, `ruff check` clean.

**Bugs caught and fixed during verification** (would have caused silent data corruption in Milestone 2+):
1. Postgres ENUM types were being created twice (once explicitly, once implicitly by `create_table`) — fixed with `create_type=False` on the inline column-level enum objects in the migration.
2. SQLAlchemy's `Enum` column type binds by Python enum *member name* (`"ACTIVE"`) by default, not member *value* (`"active"`) — silently mismatched the lowercase Postgres enum values. Fixed with a `values_callable` helper (`_str_enum`) in `orm.py`.
3. `Mapped[datetime]` columns defaulted to timezone-naive `TIMESTAMP`, but the migration created timezone-aware `TIMESTAMPTZ` columns — asyncpg rejected timezone-aware Python datetimes. Fixed by registering `datetime: DateTime(timezone=True)` in `Base.type_annotation_map` (`db.py`), so every timestamp column is tz-aware by default.

---

## Milestone 2: Agent CRUD API ✅ DONE (2026-08-10)
**Goal**: Full REST API for managing agents (no execution yet).

**Deliverables:**
- [x] API Gateway routes: POST/GET/PUT/DELETE for agents — `services/api-gateway/routers/agents.py`
- [x] Request/response schemas with validation — reuses `AgentCreate`/`AgentUpdate`/`Agent` from Milestone 1, wrapped in `agentforge_common/envelope.py`'s `DataResponse`/`ListResponse`
- [x] Database operations (async SQLAlchemy) — `services/api-gateway/crud_agents.py`, cursor-based pagination (not offset)
- [x] Error handling middleware — `agentforge_common/exceptions.py` + FastAPI exception handlers in `main.py` (404/401/409/422 mapped to the `{"error": {...}}` envelope)
- [x] API key authentication (simple, header-based) — `X-API-Key` header, hashed lookup against the `api_keys` table (`services/api-gateway/dependencies.py`, `agentforge_common/security.py`)
- [x] Auto-generated OpenAPI docs — `/docs` and `/openapi.json` confirmed serving (200)
- [x] Integration tests for all endpoints — `tests/integration/api_gateway/`, 8/8 passing against a real Postgres test database

**Done when**: Can create, list, update, delete agents via API. Swagger docs work at `/docs`. ✅ **Fully verified — both via pytest against a dedicated Postgres test DB, and manually via curl against the api-gateway service running against the real docker-compose Postgres** (health check, 401 with no key, list, create all confirmed working end-to-end).

**Bugs caught and fixed during verification** (again, only surfaced by actually running the tests, not just reading the code):
1. A stray unused import (`create_async_engine as _unused`) left over from drafting — cleaned up.
2. **Classic async-SQLAlchemy + pytest-asyncio pitfall**: a session-scoped test engine's pooled connections got bound to one test's event loop, then broke (`InterfaceError: cannot perform operation: another operation is in progress`) when a later test ran in a different loop. Fixed with `poolclass=NullPool` so every connection checkout is fresh rather than reused across loops.

**Design notes:**
- Auth reuses the `api_keys` table from Milestone 1 rather than inventing a parallel auth system — the row's `key_hash` authenticates the request; its `provider`/`encrypted_key` fields (unused until Milestone 3) will hold the user's BYOK LLM provider key.
- `scripts/seed.py` now also creates one dev API key and prints the raw value once (never stored/logged again) for local curl testing.
- Cursor pagination is real keyset pagination (`(created_at, id) > (cursor_created_at, cursor_id)`), not offset-based — matches CLAUDE.md's stated convention and stays correct under concurrent inserts.

---

## Milestone 3: Agent Execution (Core Loop) ✅ DONE (2026-08-10)
**Goal**: Run an agent — send a message, get a response, with tool calling.

**Deliverables:**
- [x] Agent runtime execution loop (think → act → observe) — `services/agent-runtime/engine.py`
- [x] LiteLLM integration (async wrapper, token tracking, cost calculation) — `services/agent-runtime/llm.py`
- [x] Tool registration and execution — `services/agent-runtime/tools.py` (ToolRegistry class)
- [x] `POST /api/v1/agents/{id}/run` endpoint — `services/api-gateway/routers/runs.py` (public, authed) calls `services/agent-runtime/routers/runs.py` (internal)
- [x] Basic token counting and cost calculation — LiteLLM `completion_cost()`, persisted as CostRecord
- [x] Execution timeout and max iterations — `asyncio.wait_for` timeout + configurable `max_iterations` loop cap
- [x] At least 2 sample tools — `get_current_time` (UTC clock) and `calculate` (safe AST math eval)
- [x] Integration tests — `tests/integration/api_gateway/test_runs_api.py`, 6/6 passing

**Done when**: Can define an agent with tools, send it a message, and get back a response that includes tool calls. Cost is tracked. ✅ **Fully verified two ways: 23/23 automated tests pass (9 unit + 8 agent CRUD + 6 run execution, mocked runtime), ruff clean — AND a live manual run against the real docker-compose stack with a real OpenAI API call (`gpt-4o-mini`), confirmed via Swagger UI on 2026-08-11: `POST /api/v1/agents/{id}/run` returned `status: "completed"` with a genuine model-generated response.**

**Architecture notes:**
- API Gateway → Agent Runtime communication is HTTP (`httpx.AsyncClient`). The gateway authenticates, looks up the agent, creates a `Run` row (status=pending→running), forwards the agent config + BYOK LLM key to the runtime, then persists Run/RunStep/CostRecord on completion.
- BYOK key flow: the `ApiKeyORM.encrypted_key` field holds the user's LLM provider key. Fallback: `OPENAI_API_KEY` env var for dev convenience.
- The execution loop iterates up to `max_iterations` times. Each iteration: call LLM → if tool_calls, execute tools and feed results back → else return. Timeout via `asyncio.wait_for`.
- Tool calls are safe: `calculate` uses AST parsing (not eval/exec), `get_current_time` is pure stdlib.

**Bugs caught during live manual verification (not caught by automated tests, since those mock the runtime call):**
1. `infra/docker/docker-compose.yml` wasn't passing `OPENAI_API_KEY` through to the `api-gateway` container's environment — the gateway is where the BYOK-fallback check happens, so the key needs to reach it, not just agent-runtime. Fixed by adding `OPENAI_API_KEY=${OPENAI_API_KEY:-}` to api-gateway's `environment:` block.
2. After a Docker Desktop restart, `docker compose up -d api-gateway` only started api-gateway and its explicit Compose `depends_on` (Postgres, Redis) — `agent-runtime` stayed stopped, since the two services are only connected via a runtime HTTP call, not a Compose dependency. Symptom: the run "succeeded" with `status: "failed"` and no error surfaced in the API response (the `Run` model doesn't expose the internal error string). Root-caused by checking `docker ps` and the agent-runtime container logs (no incoming request logged at all). Resolved by bringing up the full stack (`docker compose up -d` with no service name) rather than starting services one at a time.

---

## Milestone 4: Safety Policy Enforcement ✅ DONE (2026-08-11)
**Goal**: Define safety rules that are checked before every tool call and LLM response.

**Deliverables:**
- [x] Safety policy model (rules as strings, enforcement mode) — `SafetyPolicy` Pydantic model (M1), `SafetyChecker` class (`services/agent-runtime/safety.py`)
- [x] Pre-tool-call safety check middleware — `CheckPoint.PRE_TOOL` in engine loop, scans tool arguments before execution
- [x] Post-LLM-response safety check — `CheckPoint.POST_LLM` in engine loop, scans LLM output text after each response
- [x] Safety violation logging — violations recorded as `safety_check` type RunStep rows in Postgres
- [x] Violation response (block, warn, or log depending on policy) — `on_violation` field: block returns `[BLOCKED]` message and marks run failed, warn continues but records violation, log records silently
- [x] Tests with deliberate violation scenarios — 20 unit tests (`tests/unit/agent_runtime/test_safety.py`) + 4 integration tests (`tests/integration/api_gateway/test_safety_api.py`)

**Done when**: An agent with a policy like "never share customer PII" actually blocks a response containing PII. ✅ **Fully verified — 47/47 tests pass (20 unit safety + 9 unit models + 14 integration agent/run + 4 integration safety), ruff clean.**

**Architecture notes:**
- `SafetyChecker` supports two rule types: PII detection (regex patterns for email, phone, SSN, credit card — activated when any rule contains "pii") and keyword blocking (rules starting with `block_keywords:word1,word2`).
- Two check points in the execution loop: post-LLM (scan response text) and pre-tool (scan tool arguments). Both produce `SafetyViolation` records with the matched text, pattern name, and check point.
- Enforcement modes: `block` immediately stops the run and returns a blocked message; `warn` continues but records violations; `log` records silently.
- Safety policy flows from the API Gateway (agent's `safety_policy.rules` + `safety_policy.on_violation`) through the runtime HTTP payload to the engine's `SafetyChecker`.

**Bugs caught and fixed:**
1. Test isolation conflict: when running `pytest tests/` (unit + integration together), the unit test's `sys.path.insert(0, agent-runtime-dir)` shadowed the api-gateway's `main.py` module, causing all integration tests to fail with 500/404. Fixed by using `sys.path.append()` instead of `sys.path.insert(0, ...)` in the unit test.

---

## Milestone 5: Tracing & Observability ✅ DONE (2026-08-11)
**Goal**: Every agent run produces a full trace viewable via API.

**Deliverables:**
- [x] OpenTelemetry integration in Agent Runtime — `services/agent-runtime/tracing.py` (TracerProvider, InMemorySpanExporter, tracer)
- [x] Span creation for: LLM calls, tool calls, safety checks — `engine.py` instrumented with `tracer.start_as_current_span()` at every step
- [x] Trace storage in PostgreSQL — RunSteps (existing) + `trace_id` column on runs table (migration `0002_add_trace_id_to_runs.py`)
- [x] `GET /api/v1/runs/{id}/trace` endpoint — `services/api-gateway/routers/traces.py`, returns structured `TraceResponse` with spans timeline + `TraceSummary`
- [x] Prometheus metrics endpoint (`/metrics`) on all services — `prometheus-fastapi-instrumentator` on all 4 services + custom agent metrics (`services/agent-runtime/metrics.py`)
- [x] Grafana dashboard config (JSON provisioning) — `infra/docker/grafana/` with datasource, dashboard provider, and 10-panel dashboard JSON
- [x] Docker Compose updated with Prometheus + Grafana — `prometheus:v2.53.0` + `grafana:11.1.0` with volume mounts

**Done when**: Run an agent, then fetch its trace — see every step with timing and tokens. ✅ **Fully verified — 59/59 tests pass (8 unit tracing + 20 unit safety + 9 unit models + 18 integration agent/run/safety + 4 integration trace), ruff clean.**

**Architecture notes:**
- OTel tracing uses an in-memory span exporter that collects spans during execution. The root span (`agent.execute`) generates a `trace_id` that flows through the RunResult → API Gateway → Run record in Postgres. Child spans for LLM calls, tool executions, and safety checks carry attributes (model, tokens, cost, latency, tool name, violation count).
- The trace endpoint (`GET /api/v1/runs/{id}/trace`) reconstructs the trace from RunStep records — no separate span storage needed. Returns a `TraceResponse` with run metadata, ordered spans, and a computed `TraceSummary` (total steps/LLM calls/tool calls/safety checks/tokens/latency).
- Custom Prometheus metrics in agent-runtime: `agentforge_llm_calls_total`, `agentforge_tokens_in_total`, `agentforge_tokens_out_total`, `agentforge_cost_usd_total`, `agentforge_tool_calls_total`, `agentforge_safety_violations_total`, `agentforge_agent_run_duration_seconds`, `agentforge_llm_call_duration_seconds`.
- Grafana dashboard has 10 panels: HTTP request rate, HTTP latency p95, LLM calls total, total cost, safety violations, tool calls, token consumption rates, agent run duration percentiles, LLM call latency by model, safety violations by check point.
- Prometheus scrapes `/metrics` from all 4 services every 15s. Grafana auto-provisions the Prometheus datasource and AgentForge dashboard on startup.

---

## Milestone 6: Evaluation Pipeline ← START HERE
**Goal**: Define test suites, run agents against them, get scores.

**Deliverables:**
- [ ] Eval service with test suite CRUD
- [ ] Test case runner (calls Agent Runtime for each case)
- [ ] Scoring: accuracy (LLM-as-judge), latency, cost, tool correctness
- [ ] Version comparison endpoint
- [ ] Sample eval suite for a demo agent
- [ ] Integration tests

**Done when**: Can create a test suite with 10 cases, run it, and get a scored report with pass/fail per case.

---

## Milestone 7: Token Optimization
**Goal**: Smart routing, caching, and compression are live and measurable.

**Deliverables:**
- [ ] LiteLLM config with routing rules (simple → mini, complex → 4o)
- [ ] Redis-backed response caching
- [ ] LLMLingua integration (optional per agent)
- [ ] Cost comparison dashboard (with vs without optimization)
- [ ] Budget limit enforcement (per agent, per day)

**Done when**: Same workload costs measurably less with optimization enabled. Dashboard shows the savings.

---

## Milestone 8: Dashboard (React)
**Goal**: Web UI for managing and monitoring agents.

**Deliverables:**
- [ ] React + TypeScript + Tailwind project setup
- [ ] Agent catalog page (list, create, edit)
- [ ] Agent detail page (config, recent runs, cost)
- [ ] Trace viewer (visual timeline of agent steps)
- [ ] Eval results page (scores, version comparison)
- [ ] Cost analytics page (charts, per-agent breakdown)
- [ ] Settings page (API keys, safety policies)

**Done when**: Full platform usable through the browser. No terminal required for basic operations.

---

## Milestone 9: Infrastructure as Code
**Goal**: Production-ready deployment configs (no need to actually deploy).

**Deliverables:**
- [ ] Terraform modules for AWS (VPC, EKS, RDS, ElastiCache, S3, ECR)
- [ ] Helm charts for all services
- [ ] GitHub Actions CI/CD (lint, test, build, push images)
- [ ] Environment configs (dev, staging, prod)
- [ ] Teardown scripts (destroy all AWS resources)
- [ ] Cost estimate documentation

**Done when**: `terraform plan` succeeds. Helm charts render correctly. CI pipeline runs on push.

---

## Milestone 10: Polish & Demo
**Goal**: Portfolio-ready project.

**Deliverables:**
- [ ] Comprehensive README with screenshots/GIFs
- [ ] Architecture diagrams (Mermaid or draw.io)
- [ ] API documentation (auto-generated + examples)
- [ ] Demo video/script
- [ ] Interview talking points document
- [ ] Performance benchmarks
- [ ] Security considerations document
- [ ] Contributing guide

**Done when**: A hiring manager can clone the repo, run it in 5 minutes, and understand what it does.
