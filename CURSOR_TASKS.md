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

## Current: Milestone 0 — Project Scaffolding ✅ Claude Code side done

Claude Code has scaffolded the monorepo: directory structure, root `pyproject.toml`
(uv workspace), `packages/common` and `packages/sdk` stubs, all 4 FastAPI services
(`main.py` + `/health`), per-service `Dockerfile`s, `infra/docker/docker-compose.yml`,
`.env.example`, `.gitignore`, and `README.md`.

Verified with `uv sync --all-packages` (resolves cleanly) and by booting `api-gateway`
directly with `uv run uvicorn` — `/health` returns `{"status": "ok"}`. **Docker is not
installed on this machine**, so `docker-compose up` itself has not been run. That's the
one open item below.

Your Cursor tasks now:
- [ ] Install Docker Desktop (or Docker Engine) if not already installed
- [ ] Copy `.env.example` → `.env` and add your OpenAI API key
- [ ] Run `docker compose -f infra/docker/docker-compose.yml --env-file .env up -d` and verify all 4 services respond to `/health` (see README's "Local development" section for the exact curl commands)
- [ ] Customize `README.md` with your GitHub username and personal branding
- [ ] Initialize git repo (`git init`), make the first commit
- [ ] Create a GitHub repository and push

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
