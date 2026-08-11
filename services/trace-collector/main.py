"""Trace Collector — FastAPI entry point.

Receives span data from the Agent Runtime, stores summaries, and exposes
Prometheus metrics for the observability pipeline. Built out in Milestone 5.
"""

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

SERVICE_NAME = "trace-collector"

app = FastAPI(title="AgentForge Trace Collector", version="0.1.0")

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by Docker Compose and orchestrators."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
