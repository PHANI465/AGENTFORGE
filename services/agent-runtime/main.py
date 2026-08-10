"""Agent Runtime — FastAPI entry point.

Executes the agent think -> act -> observe loop: tool orchestration, safety
policy enforcement, context management, streaming responses. Stubbed in
Milestone 0; execution loop lands in Milestone 3.
"""

from fastapi import FastAPI

SERVICE_NAME = "agent-runtime"

app = FastAPI(title="AgentForge Agent Runtime", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by Docker Compose and orchestrators."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
