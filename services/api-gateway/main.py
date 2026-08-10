"""API Gateway — FastAPI entry point.

REST API for CRUD on agents/tools/policies, auth, rate limiting, and routing
to the Agent Runtime and Eval Service. Stubbed in Milestone 0; routes land in
Milestone 2 (Agent CRUD API).
"""

from fastapi import FastAPI

SERVICE_NAME = "api-gateway"

app = FastAPI(title="AgentForge API Gateway", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by Docker Compose and orchestrators."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
