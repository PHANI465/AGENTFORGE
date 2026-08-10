# Build context is the repo root (see infra/docker/docker-compose.yml)
FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
COPY packages ./packages
COPY services/eval-service ./services/eval-service

RUN uv sync --no-dev --package eval-service

WORKDIR /app/services/eval-service

EXPOSE 8002

CMD ["uv", "run", "--project", "/app", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
