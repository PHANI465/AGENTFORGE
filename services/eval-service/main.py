"""Eval Service — FastAPI entry point.

Test suite CRUD, test case runner, scoring (accuracy, latency, cost, tool
correctness), version comparison. Stubbed in Milestone 0; built out in
Milestone 6 (Evaluation Pipeline).
"""

from fastapi import FastAPI

SERVICE_NAME = "eval-service"

app = FastAPI(title="AgentForge Eval Service", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by Docker Compose and orchestrators."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
