# Build context is the repo root (see infra/docker/docker-compose.yml)
FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
COPY packages ./packages
COPY services/api-gateway ./services/api-gateway
# scripts/seed.py --reset is what the demo-reset CronJob runs (see
# infra/helm/agentforge/templates/cronjob-demo-reset.yaml) — reusing this
# image (it already has agentforge_common, which is all the script needs)
# avoids a whole separate image/ECR-repo/CI-matrix-entry for one script.
COPY scripts ./scripts

RUN uv sync --no-dev --package api-gateway

WORKDIR /app/services/api-gateway

EXPOSE 8000

CMD ["uv", "run", "--project", "/app", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
