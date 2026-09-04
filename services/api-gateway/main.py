"""API Gateway — FastAPI entry point.

REST API for CRUD on agents/tools/policies, auth, rate limiting, and routing
to the Agent Runtime and Eval Service. Agent CRUD lands in Milestone 2;
routing to Agent Runtime/Eval Service lands in later milestones.
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from agentforge_common.db import engine as db_engine
from agentforge_common.envelope import ErrorDetail, ErrorResponse
from agentforge_common.exceptions import (
    AgentForgeError,
    BudgetExceededError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from agentforge_common.logging import setup_logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from middleware import RequestIDMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from rate_limit import limiter
from routers.agents import router as agents_router
from routers.analytics import router as analytics_router
from routers.api_keys import router as api_keys_router
from routers.demo import router as demo_router
from routers.evals import router as evals_router
from routers.runs import router as runs_router
from routers.traces import router as traces_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

SERVICE_NAME = "api-gateway"
setup_logging(SERVICE_NAME)
log = structlog.get_logger(service=SERVICE_NAME)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("starting", service=SERVICE_NAME)
    yield
    log.info("shutting_down", service=SERVICE_NAME)
    await db_engine.dispose()
    log.info("db_pool_closed", service=SERVICE_NAME)


app = FastAPI(title="AgentForge API Gateway", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_dashboard_origins = os.getenv(
    "DASHBOARD_ORIGINS", "http://localhost:3001,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_dashboard_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.add_middleware(RequestIDMiddleware)

app.include_router(agents_router)
app.include_router(runs_router)
app.include_router(traces_router)
app.include_router(evals_router)
app.include_router(analytics_router)
app.include_router(api_keys_router)
app.include_router(demo_router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

_STATUS_BY_ERROR = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
    ConflictError: status.HTTP_409_CONFLICT,
    BudgetExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
}


@app.exception_handler(AgentForgeError)
async def agentforge_error_handler(_request: Request, exc: AgentForgeError) -> JSONResponse:
    status_code = _STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST)
    log.warning("request_error", code=exc.code, message=exc.message, status=status_code)
    body = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(code="validation_error", message=str(exc.errors()))
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body.model_dump())


@app.get("/health")
async def health() -> dict[str, Any]:
    """Deep health check — reports downstream dependency status."""
    checks: dict[str, str] = {}

    try:
        from sqlalchemy import text

        async with db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    try:
        import redis.asyncio as aioredis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = aioredis.from_url(redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
