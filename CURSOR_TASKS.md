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

Your Cursor tasks now:
- [ ] Copy `.env.example` → `.env` and add your OpenAI API key (needed by Milestone 3, do whenever)
- [ ] Customize `README.md` with your GitHub username and personal branding (cosmetic, optional)
- [ ] Commit and push the Milestone 1 changes (`git add`, `git commit`, `git push`) — remember: no AI co-author trailer
- [ ] Optional: browse the seeded data yourself — `psql postgresql://agentforge:agentforge@localhost:5432/agentforge` or any Postgres GUI (TablePlus, DBeaver) to see the sample agent/run/eval rows

## Current: Milestone 2 — Agent CRUD API

Claude Code will handle this next: FastAPI routes for full agent CRUD, request/response
schemas, API key auth, error handling middleware, OpenAPI docs, integration tests.
No Cursor tasks yet — they'll appear here once scaffolded.

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
