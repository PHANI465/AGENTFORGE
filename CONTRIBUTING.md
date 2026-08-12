# Contributing to AgentForge

AgentForge is currently a single-maintainer project — this guide exists so
the workflow is documented and reproducible, whether that's future-you six
months from now or someone else picking it up.

## Dev setup

Requires [Docker](https://www.docker.com/), [uv](https://docs.astral.sh/uv/),
and [Node 22](https://nodejs.org/) (for the dashboard).

```bash
git clone https://github.com/PHANI465/AGENTFORGE.git
cd AGENTFORGE
cp .env.example .env          # add your OpenAI API key
uv sync --all-packages
docker compose -f infra/docker/docker-compose.yml --env-file .env up -d
uv run python scripts/seed.py # prints a dev API key
```

Dashboard dev server (hot reload, separate from the Docker image):

```bash
cd dashboard
npm ci
npm run dev
```

## Project structure and conventions

Full conventions live in [`CLAUDE.md`](CLAUDE.md) — read it before writing
code. The short version:

- Python 3.11+, type hints everywhere, Pydantic models for all data shapes,
  `async def` for I/O, f-strings, Google-style docstrings on public
  functions.
- `snake_case.py` files, `PascalCase` classes, `/api/v1/kebab-case` endpoints,
  `snake_case` plural DB tables.
- Every API response uses the shared envelope:
  `{"data": ..., "meta": ...}` on success, `{"error": {"code", "message"}}`
  on failure (`agentforge_common/envelope.py`).
- Conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`,
  `chore:`), small focused PRs.

## Before opening a PR

```bash
uv run ruff check .                 # lint
uv run pytest tests/ -q             # unit + integration tests (needs Postgres — see below)
cd dashboard && npm run lint && npm run build
```

Integration tests need a real Postgres reachable at `localhost:5432` with
`agentforge`/`agentforge` credentials — the `docker compose up` from Dev
Setup already provides this. CI (`.github/workflows/ci.yml`) runs the same
three checks plus a Docker build of all 5 service images on every push/PR —
if it's green locally, it should be green there too.

## Adding a new service

1. `services/<name>/` — FastAPI app + `Dockerfile` (copy an existing
   service's shape — they're deliberately uniform).
2. Add it to the root `pyproject.toml` workspace members.
3. Add it to `infra/docker/docker-compose.yml`.
4. Add it to `infra/helm/agentforge/values.yaml`'s `services:` map — the
   Deployment/Service/HPA templates are data-driven, so a values.yaml entry
   is all a new service needs there.
5. Add it to the `docker-build` matrix in `.github/workflows/ci.yml` and the
   `push-ghcr`/`push-ecr` matrices in `cd.yml`.

## Database changes

Schema changes go through Alembic (`packages/common/alembic/`):

```bash
cd packages/common
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

Test fixtures (`tests/integration/*/conftest.py`) create tables directly from
ORM metadata rather than running migrations — fast test setup — so a schema
change needs both the ORM model (`agentforge_common/orm.py`) and a matching
Alembic migration to stay in sync.

## Reporting bugs / requesting features

This being a personal project, there's no formal issue tracker workflow yet —
open a GitHub issue with what you observed, what you expected, and how to
reproduce it (a `curl` command or a failing test is ideal).
