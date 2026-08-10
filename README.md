# AgentForge

**Agent-native AI platform** — build, deploy, evaluate, monitor, and govern autonomous AI agents. Think "Vercel for AI agents": a production platform for teams that define agents, push them live, run evaluations, track costs, and enforce safety policies, instead of another LLM chatbot wrapper.

> Full project context lives in [CLAUDE.md](CLAUDE.md), system design in [ARCHITECTURE.md](ARCHITECTURE.md), and the build plan in [MILESTONES.md](MILESTONES.md).

## What makes it agent-native

Most LLM-ops tools (LangSmith, Humanloop) log request/response pairs. AgentForge is built for **autonomous agents** that run multi-step reasoning loops, call external tools, branch on results, talk to other agents, and must follow safety and governance rules — so the platform tracks the whole run, not just the API call.

## Architecture at a glance

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

Six core components: **Python SDK**, **API Gateway** (FastAPI), **Agent Runtime** (execution loop + safety enforcement), **Token Optimization Layer** (LiteLLM + optional LLMLingua), **Evaluation Pipeline**, and the **Observability Stack** (OpenTelemetry + Prometheus + Grafana), fronted by a React **Dashboard**. See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

## Tech stack

Python 3.11+ / FastAPI · PostgreSQL · Redis · Docker Compose (local) / Kubernetes via Helm (prod) · LiteLLM · OpenTelemetry / Prometheus / Grafana · React + TypeScript + Tailwind · Terraform (AWS/EKS, not required to run locally).

## Project structure

```
agentforge/
├── services/           # api-gateway, agent-runtime, eval-service, trace-collector (FastAPI)
├── packages/
│   ├── sdk/             # agentforge — the Python SDK
│   └── common/           # agentforge_common — shared models/utils
├── dashboard/           # React + TS + Tailwind UI (Milestone 8)
├── infra/
│   ├── docker/           # docker-compose.yml + per-service Dockerfiles
│   ├── terraform/         # AWS infra as code
│   ├── helm/              # Kubernetes charts
│   └── github-actions/    # CI/CD workflows
├── tests/               # unit, integration, e2e
├── docs/                # diagrams, API docs, ADRs
└── scripts/             # dev setup/seed/teardown
```

## Local development

Requires [Docker](https://www.docker.com/) and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env          # add your OpenAI API key
docker compose -f infra/docker/docker-compose.yml --env-file .env up -d
```

Services then available at:

| Service | URL |
|---|---|
| API Gateway | http://localhost:8000 |
| Agent Runtime | http://localhost:8001 |
| Eval Service | http://localhost:8002 |
| Trace Collector | http://localhost:8003 |
| Dashboard | http://localhost:3000 *(Milestone 8)* |
| LiteLLM Proxy | http://localhost:4000 *(Milestone 3/7)* |
| Grafana | http://localhost:3001 *(Milestone 5)* |
| Prometheus | http://localhost:9090 *(Milestone 5)* |

Check everything is up:

```bash
curl localhost:8000/health
curl localhost:8001/health
curl localhost:8002/health
curl localhost:8003/health
```

Each should return `{"status": "ok"}`.

### Running a service without Docker

```bash
uv sync --package api-gateway
cd services/api-gateway
uv run --project ../.. uvicorn main:app --reload --port 8000
```

## Status

Currently on **Milestone 0: Project Scaffolding** — see [MILESTONES.md](MILESTONES.md) for the full build plan and [CURSOR_TASKS.md](CURSOR_TASKS.md) for what's parallelizable in Cursor.

## License

TBD.
