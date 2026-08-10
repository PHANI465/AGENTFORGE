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

## Milestone 2: Agent CRUD API ← START HERE
**Goal**: Full REST API for managing agents (no execution yet).

**Deliverables:**
- [ ] API Gateway routes: POST/GET/PUT/DELETE for agents
- [ ] Request/response schemas with validation
- [ ] Database operations (async SQLAlchemy)
- [ ] Error handling middleware
- [ ] API key authentication (simple, header-based)
- [ ] Auto-generated OpenAPI docs
- [ ] Integration tests for all endpoints

**Done when**: Can create, list, update, delete agents via API. Swagger docs work at `/docs`.

---

## Milestone 3: Agent Execution (Core Loop)
**Goal**: Run an agent — send a message, get a response, with tool calling.

**Deliverables:**
- [ ] Agent runtime execution loop (think → act → observe)
- [ ] LiteLLM integration (proxy setup, API key routing)
- [ ] Tool registration and execution
- [ ] `POST /api/v1/agents/{id}/run` endpoint
- [ ] Basic token counting and cost calculation
- [ ] Execution timeout and max iterations
- [ ] At least 2 sample tools (e.g., `search_web`, `get_weather`)
- [ ] Integration tests

**Done when**: Can define an agent with tools, send it a message, and get back a response that includes tool calls. Cost is tracked.

---

## Milestone 4: Safety Policy Enforcement
**Goal**: Define safety rules that are checked before every tool call and LLM response.

**Deliverables:**
- [ ] Safety policy model (rules as strings, enforcement mode)
- [ ] Pre-tool-call safety check middleware
- [ ] Post-LLM-response safety check
- [ ] Safety violation logging
- [ ] Violation response (block, warn, or log depending on policy)
- [ ] Tests with deliberate violation scenarios

**Done when**: An agent with a policy like "never share customer PII" actually blocks a response containing PII.

---

## Milestone 5: Tracing & Observability
**Goal**: Every agent run produces a full trace viewable via API.

**Deliverables:**
- [ ] OpenTelemetry integration in Agent Runtime
- [ ] Span creation for: LLM calls, tool calls, safety checks
- [ ] Trace storage in PostgreSQL
- [ ] `GET /api/v1/runs/{id}/trace` endpoint
- [ ] Prometheus metrics endpoint (`/metrics`) on all services
- [ ] Grafana dashboard config (JSON provisioning)
- [ ] Docker Compose updated with Prometheus + Grafana

**Done when**: Run an agent, then fetch its trace — see every step with timing and tokens.

---

## Milestone 6: Evaluation Pipeline
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
