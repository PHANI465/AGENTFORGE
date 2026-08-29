# AgentForge — Project Context

> This file is the single source of truth for AI assistants (Claude Code, Cursor) working on this project.
> Read this FIRST before writing any code.

---

## What Is AgentForge?

AgentForge is an **agent-native AI platform** — an internal developer platform for AI startups to build, deploy, evaluate, monitor, and govern autonomous AI agents.

Think "Vercel for AI agents." Not a chatbot wrapper. Not another LangChain tutorial. A production platform where teams define agents, push them to production, run evaluations, track costs, and enforce safety policies.

### What Makes It Agent-Native (vs LLM Ops)?

Most existing tools (LangSmith, Humanloop) focus on LLM API calls — request/response logging. AgentForge is built for **autonomous agents** that:
- Execute multi-step reasoning loops
- Call external tools (APIs, databases, functions)
- Make decisions and branch based on results
- Communicate with other agents
- Must follow safety policies and governance rules

---

## Target Users

AI/ML Engineers at startups who need to move agents from prototype to production. They can write Python, they understand APIs, but they don't want to build deployment infrastructure, evaluation pipelines, and monitoring dashboards from scratch.

---

## Core Architecture

```
┌──────────────────────────────────────────────────────┐
│                    AgentForge Platform                │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │  Python SDK — define agents, tools, policies  │    │
│  └──────────────────┬───────────────────────────┘    │
│                     │                                │
│  ┌──────────────────▼───────────────────────────┐    │
│  │  API Gateway (FastAPI) — REST, auth, routing  │    │
│  └──────────────────┬───────────────────────────┘    │
│                     │                                │
│  ┌──────────────────▼───────────────────────────┐    │
│  │  Agent Runtime                                │    │
│  │  ┌────────────┐ ┌──────────┐ ┌─────────────┐ │    │
│  │  │ Execution  │ │  Tool    │ │   Safety    │ │    │
│  │  │  Engine    │ │ Orchestr.│ │ Enforcement │ │    │
│  │  └────────────┘ └──────────┘ └─────────────┘ │    │
│  └──────────────────┬───────────────────────────┘    │
│                     │                                │
│  ┌──────────────────▼───────────────────────────┐    │
│  │  Token Optimization Layer                     │    │
│  │  LiteLLM (routing + caching + cost tracking)  │    │
│  │  + LLMLingua (prompt compression, optional)   │    │
│  └──────────────────┬───────────────────────────┘    │
│                     │                                │
│  ┌─────────┐  ┌─────▼─────┐  ┌──────────────────┐   │
│  │  Eval   │  │ Observ.   │  │    Dashboard     │   │
│  │Pipeline │  │ (OTel +   │  │    (React)       │   │
│  │         │  │ Prometheus)│  │                  │   │
│  └─────────┘  └───────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────┘
```

See `ARCHITECTURE.md` for detailed component descriptions.

---

## Tech Stack

### Core (Mandatory)
| Technology | Purpose | Why |
|---|---|---|
| **Python 3.11+** | All backend services | Industry standard for AI/ML |
| **FastAPI** | API Gateway + service APIs | Async, auto-docs, type-safe |
| **PostgreSQL** | Primary database | Agents, configs, eval results, audit logs |
| **Redis** | Caching + message broker | LiteLLM cache, session state, pub/sub |
| **Docker** | Containerization | All services containerized |
| **Docker Compose** | Local development | One command to spin up everything |

### Token Optimization
| Technology | Purpose | Why |
|---|---|---|
| **LiteLLM** | LLM proxy, routing, caching, cost tracking | 53K+ stars, handles 140+ providers, don't reinvent |
| **LLMLingua** | Prompt compression (optional) | Microsoft Research, up to 20x compression |

### Observability
| Technology | Purpose | Why |
|---|---|---|
| **OpenTelemetry** | Distributed tracing | Vendor-neutral, traces every agent step |
| **Prometheus** | Metrics collection | Industry standard for K8s environments |
| **Grafana** | Dashboards + alerting | Visualize metrics, set up alerts |

### Frontend
| Technology | Purpose | Why |
|---|---|---|
| **React + TypeScript** | Dashboard UI | Component-based, type-safe |
| **Tailwind CSS** | Styling | Utility-first, fast iteration |

### Infrastructure (Production-Ready Configs)
| Technology | Purpose | Why |
|---|---|---|
| **Terraform** | AWS infrastructure as code | Reproducible, version-controlled infra |
| **Helm** | Kubernetes deployment | Templated K8s manifests |
| **GitHub Actions** | CI/CD | Free for public repos |

### LLM Provider (Initial)
| Provider | Why |
|---|---|
| **OpenAI (GPT-4o, GPT-4o-mini)** | Start simple with one provider. LiteLLM makes adding more providers trivial later. |

---

## Project Structure

```
agentforge/
├── CLAUDE.md              ← You are here
├── ARCHITECTURE.md        ← Detailed system design
├── MILESTONES.md          ← Ordered build plan
├── CURSOR_TASKS.md        ← Tasks for parallel Cursor work
│
├── services/
│   ├── api-gateway/       ← FastAPI gateway (auth, routing)
│   ├── agent-runtime/     ← Core execution engine
│   ├── eval-service/      ← Evaluation pipeline
│   └── trace-collector/   ← OpenTelemetry collector + storage
│
├── packages/
│   ├── sdk/               ← Python SDK (agentforge package)
│   └── common/            ← Shared models, utils, exceptions
│
├── dashboard/             ← React frontend
│
├── infra/
│   ├── docker/            ← Dockerfiles + docker-compose.yml
│   ├── terraform/         ← AWS infrastructure
│   ├── helm/              ← Kubernetes Helm charts
│   └── github-actions/    ← CI/CD workflows
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/
│   ├── diagrams/          ← Architecture diagrams
│   ├── api/               ← API documentation
│   └── decisions/         ← ADRs (Architecture Decision Records)
│
├── scripts/               ← Dev scripts (setup, seed, teardown)
├── pyproject.toml         ← Python project config (monorepo)
└── README.md              ← Public-facing project description
```

---

## Coding Conventions

### Python
- **Type hints everywhere** — every function signature, every return type
- **Pydantic models** for all data structures (request/response, configs, domain objects)
- **Async by default** — use `async def` for all I/O-bound operations
- **Dependency injection** via FastAPI's `Depends()`
- **No bare exceptions** — catch specific exception types
- **Docstrings** on all public functions and classes (Google style)
- **f-strings** over `.format()` or `%`

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- API endpoints: `/api/v1/kebab-case`
- Database tables: `snake_case`, plural (`agents`, `eval_runs`)

### API Design
- RESTful with consistent patterns
- Always return structured responses: `{"data": ..., "meta": ...}` for success, `{"error": {"code": ..., "message": ...}}` for errors
- Use HTTP status codes correctly (201 for create, 404 for not found, etc.)
- Version all APIs: `/api/v1/...`
- Pagination: cursor-based for lists

### Testing
- `pytest` for all tests
- Test files mirror source structure: `services/api-gateway/routes/agents.py` → `tests/unit/api-gateway/routes/test_agents.py`
- Aim for unit tests on business logic, integration tests on API endpoints
- Use factories/fixtures, not raw object construction

### Git
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Feature branches: `feat/agent-runtime-execution-loop`
- Small, focused PRs — one feature or fix per PR

---

## Workflow Rules

### Step-by-Step Execution
This project is built incrementally. After every implementation session:
1. **Report what was done** — files created/modified, features implemented
2. **Report what's next** — the next milestone or task
3. **Report Cursor tasks** — what can be done in parallel in Cursor IDE

### Claude Code vs Cursor Split
- **Claude Code**: Core architecture, complex multi-file features, API design, service scaffolding, integration work
- **Cursor**: Individual component implementation, styling, unit tests, config files, Helm charts, Terraform modules

### Quality Gates
Before marking any milestone complete:
- [ ] Code compiles/runs without errors
- [ ] Basic tests pass
- [ ] Docker Compose starts all services
- [ ] API endpoints respond correctly
- [ ] No hardcoded secrets or credentials

---

## Key Architectural Decisions

### ADR-001: Use LiteLLM as LLM Proxy
- **Decision**: Use LiteLLM instead of building a custom LLM proxy
- **Rationale**: 53K+ stars, handles routing/caching/cost tracking/budgets out of the box. Building our own would take months to replicate.
- **Consequence**: LiteLLM is a core dependency. Agent runtime calls LLMs through LiteLLM's API.

### ADR-002: BYOK (Bring Your Own Key) Model
- **Decision**: Users provide their own LLM API keys. AgentForge never pays for LLM usage.
- **Rationale**: Avoids billing complexity. Users control their own spend. We track costs by counting tokens × public pricing.
- **Consequence**: Need secure key storage (encrypted at rest). LiteLLM virtual keys handle per-user routing.

### ADR-003: Docker Compose for Dev, K8s for Prod
- **Decision**: Local development uses Docker Compose. Production configs use Helm charts targeting EKS.
- **Rationale**: $0 AWS budget means no always-on EKS cluster. Docker Compose gives the full platform locally. Helm charts prove K8s knowledge without cost.
- **Consequence**: All services must work in both environments. Use environment variables for config, never hardcode hosts/ports.

### ADR-004: Monorepo
- **Decision**: Single repository for all services, SDK, dashboard, and infra.
- **Rationale**: Easier dependency management, atomic commits across services, simpler CI/CD. At our scale (one developer), monorepo is clearly better.
- **Consequence**: Use Python workspaces (pyproject.toml) for package management. Docker builds use multi-stage with specific service contexts.

### ADR-005: Real AWS/K8s Deployment Is Opt-In, Not the Default
- **Decision**: The Terraform/Helm production path can now be genuinely applied (Route53 + ACM + AWS Load Balancer Controller + external-dns, `.github/workflows/infra-apply.yml`), but only via a manual, gated `workflow_dispatch` — never automatically on push. ADR-003's $0-by-default posture stands; this ADR only says the production path is no longer purely aspirational.
- **Rationale**: Going public needs real DNS/TLS, which ADR-003 didn't cover. But auto-applying on every merge would silently start real billing and risks unattended infra drift on a solo-maintained project with no infra review gate — the opposite of ADR-003's cost-consciousness.
- **Consequence**: `enable_tls` defaults to `false` in every environment's `.tfvars` (see `docs/deployment-runbook.md`); flipping it on and running `infra-apply.yml` is a deliberate, one-at-a-time action, not a side effect of shipping a feature.

---

## AWS Constraints
- **Budget**: $0 — Free Tier only
- **Strategy**: Everything runs locally via Docker Compose. Terraform configs and Helm charts target AWS/EKS but are not required to run the platform.
- **If a service needs AWS**: Document the expected monthly cost and provide a local alternative.

---

## Current Status
- **Phase**: Project scaffolding (Milestone 0)
- **Next**: See `MILESTONES.md` for the current milestone
