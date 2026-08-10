"""Trace Collector — FastAPI entry point.

Receives OpenTelemetry spans emitted by the Agent Runtime, stores them, and
serves the trace query API used by the Dashboard. Stubbed in Milestone 0;
built out in Milestone 5 (Tracing & Observability).
"""

from fastapi import FastAPI

SERVICE_NAME = "trace-collector"

app = FastAPI(title="AgentForge Trace Collector", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by Docker Compose and orchestrators."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
