"""Trace Collector — FastAPI entry point.

Receives span data from the Agent Runtime, stores summaries, and exposes
Prometheus metrics for the observability pipeline. Built out in Milestone 5.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from agentforge_common.db import engine as db_engine
from agentforge_common.logging import setup_logging
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

SERVICE_NAME = "trace-collector"
setup_logging(SERVICE_NAME)
log = structlog.get_logger(service=SERVICE_NAME)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("starting", service=SERVICE_NAME)
    yield
    log.info("shutting_down", service=SERVICE_NAME)
    await db_engine.dispose()


app = FastAPI(title="AgentForge Trace Collector", version="0.1.0", lifespan=lifespan)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by Docker Compose and orchestrators."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
