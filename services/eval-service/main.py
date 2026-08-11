"""Eval Service — FastAPI entry point.

Executes eval suites: runs each test case against an agent via the Agent
Runtime, scores results (LLM-as-judge accuracy, tool correctness), and
returns scored results to the API Gateway for persistence.
"""

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from routers.evals import router as evals_router

SERVICE_NAME = "eval-service"

app = FastAPI(title="AgentForge Eval Service", version="0.1.0")
app.include_router(evals_router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by Docker Compose and orchestrators."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
