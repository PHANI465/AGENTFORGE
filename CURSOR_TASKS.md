# AgentForge — Cursor Tasks

> Things to build in Cursor IDE, in parallel with Claude Code work.
> Updated after every milestone.

---

## How This Works

After every Claude Code session, this file gets updated with tasks you can do in Cursor. These are typically:
- Individual component implementations
- Styling and UI work
- Config files (Dockerfiles, Helm charts, Terraform)
- Unit tests
- Small utilities

Open this file in Cursor → pick a task → build it → check it off.

---

## Milestone 0 — Project Scaffolding ✅ FULLY DONE (2026-08-10)

Scaffolded and verified: monorepo structure, root `pyproject.toml` (uv workspace),
`packages/common` and `packages/sdk` stubs, all 4 FastAPI services (`main.py` +
`/health`), per-service `Dockerfile`s, `infra/docker/docker-compose.yml`,
`.env.example`, `.gitignore`, `README.md`. `docker compose up` confirmed working —
all 4 services (`8000`–`8003`) responded `{"status": "ok"}` on `/health`. Pushed to
GitHub at https://github.com/PHANI465/AGENTFORGE — sole contributor, no AI
co-author trailers on any commit.

- [x] Install Docker Desktop (or Docker Engine)
- [x] Run `docker compose -f infra/docker/docker-compose.yml --env-file .env up -d` and verify all 4 services respond to `/health`
- [x] Initialize git repo (`git init`), make the first commit
- [x] Create a GitHub repository and push
- [ ] Copy `.env.example` → `.env` and add your OpenAI API key (not needed until Milestone 3, do whenever)
- [ ] Customize `README.md` with your GitHub username and personal branding (cosmetic, optional)

## Milestone 1 — Shared Models & Database ✅ FULLY DONE (2026-08-10)

Claude Code built and fully verified against the live Postgres container:
Pydantic models (`packages/common/agentforge_common/models.py`, `enums.py`),
async SQLAlchemy setup (`db.py`), ORM models for all 9 tables (`orm.py`),
Alembic migration (`packages/common/alembic/versions/0001_initial_schema.py`),
a seed script (`scripts/seed.py`), and unit tests (`tests/unit/common/test_models.py`,
9/9 passing). `alembic upgrade head` / `downgrade base` round-tripped cleanly;
seed data confirmed in every table by direct query; `ruff check` clean.

Three real bugs were caught and fixed during verification (double enum-type
creation, enum member-name vs. value mismatch, naive vs. timezone-aware
datetime columns) — see MILESTONES.md for details. None of this would have
been caught without actually running migrations against a live database.

- [x] Commit and push the Milestone 1 changes — done
- [ ] Copy `.env.example` → `.env` and add your OpenAI API key (needed by Milestone 3, do whenever)
- [ ] Customize `README.md` with your GitHub username and personal branding (cosmetic, optional)

## Milestone 2 — Agent CRUD API ✅ FULLY DONE (2026-08-10)

Full REST API for agents is live: `POST/GET/PUT/DELETE /api/v1/agents` (+ list with
cursor pagination), `X-API-Key` header auth against the `api_keys` table, structured
error envelope, OpenAPI docs at `/docs`. Verified two ways: 8/8 integration tests
passing against a dedicated Postgres test database, AND manually via curl against
the api-gateway service running against the real docker-compose Postgres (health,
401-without-key, list, create all confirmed). `scripts/seed.py` now prints a dev API
key you can use for manual testing. See MILESTONES.md for the two real bugs caught
and fixed during verification (a pytest-asyncio + async-SQLAlchemy event-loop pitfall
was the interesting one).

Your Cursor tasks now:
- [ ] Commit and push the Milestone 2 changes — no AI co-author trailer
- [ ] Try the API yourself: run `docker compose -f infra/docker/docker-compose.yml --env-file .env up -d --build` (rebuild picks up the new code), then `docker compose -f infra/docker/docker-compose.yml exec api-gateway python /app/scripts/seed.py` won't work as-is (seed.py isn't copied into the container image) — easier to just run `uv run python scripts/seed.py` locally against the compose Postgres, grab the printed dev key, and hit `http://localhost:8000/docs` in a browser to try the endpoints interactively via Swagger's "Try it out"
- [ ] Copy `.env.example` → `.env` and add your OpenAI API key (needed by Milestone 3)
- [ ] Customize `README.md` with your GitHub username and personal branding (cosmetic, optional)

## Milestone 3 — Agent Execution (Core Loop) ✅ FULLY DONE (2026-08-10)

The core execution engine is live: think→act→observe loop with LiteLLM integration,
tool registry (2 built-in tools: `get_current_time`, `calculate`), token counting,
cost calculation, timeout + max iterations. `POST /api/v1/agents/{id}/run` on the
API Gateway authenticates, looks up the agent, calls the agent-runtime service via
HTTP, and persists Run/RunStep/CostRecord rows to Postgres. 23/23 tests passing
(9 unit + 8 agent CRUD + 6 run execution), ruff clean.

Your Cursor tasks now:
- [x] Add your OpenAI API key to `.env` as `OPENAI_API_KEY=sk-...` — done
- [x] Rebuild containers and add `OPENAI_API_KEY` passthrough to api-gateway in docker-compose.yml — done
- [x] Try it end-to-end — done and confirmed 2026-08-11: real `gpt-4o-mini` call via Swagger, `status: "completed"`
- [ ] **Commit and push Milestones 2 + 3 changes together — no AI co-author trailer** (still pending)
- [ ] Customize `README.md` with your GitHub username and personal branding (cosmetic, optional)

## Milestone 4 — Safety Policy Enforcement ✅ FULLY DONE (2026-08-11)

Safety checker with PII detection (email, phone, SSN, credit card regex) and
keyword blocking, integrated at two check points in the execution engine
(post-LLM response, pre-tool call). Three enforcement modes: block (stops run,
returns `[BLOCKED]` message), warn (continues but records), log (silent). Safety
policy flows from the agent's config through the API Gateway → Runtime HTTP call.
47/47 tests passing (20 unit safety + 9 unit models + 14 integration agent/run +
4 integration safety), ruff clean.

Your Cursor tasks now:
- [ ] **Commit and push Milestones 2 + 3 + 4 changes together — no AI co-author trailer** (still pending)
- [ ] Try safety enforcement: create an agent with `safety_policy.rules: ["never share customer PII"]` and `on_violation: "block"`, then run it with a prompt that would elicit PII — verify the response is blocked
- [ ] Customize `README.md` with your GitHub username and personal branding (cosmetic, optional)

## Milestone 5 — Tracing & Observability ✅ FULLY DONE (2026-08-11)

Full observability pipeline: OTel instrumentation in agent-runtime engine (root
span + child spans for LLM/tool/safety calls with attributes), trace_id stored on
Run records (Alembic migration 0002), `GET /api/v1/runs/{id}/trace` endpoint with
structured TraceResponse + TraceSummary, Prometheus `/metrics` on all 4 services
with custom agent metrics (LLM calls, tokens, cost, safety violations, run duration,
LLM latency), Grafana dashboard (10 panels) auto-provisioned, Prometheus + Grafana
added to Docker Compose. 59/59 tests passing, ruff clean.

Your Cursor tasks now:
- [ ] **Commit and push Milestone 5 changes — no AI co-author trailer**
- [ ] `docker compose up -d --build` to rebuild all services, then run `alembic upgrade head` to add the trace_id column
- [ ] Try the trace endpoint: run an agent, then `GET /api/v1/runs/{run_id}/trace` to see the full trace
- [ ] Visit Grafana at `http://localhost:3000` (admin/agentforge) and check the AgentForge dashboard
- [ ] Visit Prometheus at `http://localhost:9090` and check that all targets are up

## Milestone 6 — Evaluation Pipeline ✅ FULLY DONE (2026-08-11)

Full eval pipeline: eval suite CRUD on the API Gateway (`/api/v1/eval-suites`),
a stateless eval-service that runs each test case against an agent via
agent-runtime and scores it (LLM-as-judge accuracy + tool-call correctness),
persisted `EvalRun`/`EvalResult` rows with a computed summary (pass rate, avg
latency, total cost, total tokens), and a version-comparison endpoint
(`GET /api/v1/eval-runs/{id}/compare/{other_id}`). 78/78 tests passing
(12 new scoring unit tests + 7 new eval integration tests), ruff clean.

Your Cursor tasks now:
- [ ] **Commit and push Milestone 6 changes — no AI co-author trailer**
- [ ] `docker compose up -d --build` to rebuild all services (eval-service now does real work instead of being a stub)
- [ ] Try it: `POST /api/v1/eval-suites` with a suite (or use the one `scripts/seed.py` already creates), then `POST /api/v1/eval-suites/{id}/run`, then `GET /api/v1/eval-runs/{id}` to see the scored results
- [ ] Run the same suite twice against slightly different agent configs, then hit `GET /api/v1/eval-runs/{id}/compare/{other_id}` to see the pass-rate/latency/cost deltas

## Next: Milestone 7 — Token Optimization

Claude Code will handle this next: LiteLLM routing rules (simple→mini, complex→4o),
Redis-backed response caching, optional LLMLingua prompt compression, cost
comparison dashboard, budget limit enforcement.

---

## Backlog (Future Cursor Tasks)

These will be assigned to specific milestones as we progress:

### Infrastructure
- [ ] Write Dockerfile for each service (multi-stage builds)
- [ ] Write Helm chart values for each service
- [ ] Write Terraform modules (VPC, EKS, RDS)
- [ ] GitHub Actions CI pipeline

### Frontend
- [ ] Dashboard project setup (React + TS + Tailwind)
- [ ] Reusable UI components (Button, Card, Table, Modal)
- [ ] Agent list page
- [ ] Agent detail page
- [ ] Trace viewer component
- [ ] Cost chart components

### Testing
- [ ] Unit test fixtures and factories
- [ ] Integration test setup (test database, test client)
- [ ] E2E test with sample agent

### DevEx
- [ ] Pre-commit hooks (ruff, mypy)
- [ ] Makefile with common commands
- [ ] Local development documentation
