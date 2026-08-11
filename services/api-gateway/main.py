"""API Gateway — FastAPI entry point.

REST API for CRUD on agents/tools/policies, auth, rate limiting, and routing
to the Agent Runtime and Eval Service. Agent CRUD lands in Milestone 2;
routing to Agent Runtime/Eval Service lands in later milestones.
"""

from agentforge_common.envelope import ErrorDetail, ErrorResponse
from agentforge_common.exceptions import (
    AgentForgeError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from routers.agents import router as agents_router
from routers.evals import router as evals_router
from routers.runs import router as runs_router
from routers.traces import router as traces_router

SERVICE_NAME = "api-gateway"

app = FastAPI(title="AgentForge API Gateway", version="0.1.0")

app.include_router(agents_router)
app.include_router(runs_router)
app.include_router(traces_router)
app.include_router(evals_router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

_STATUS_BY_ERROR = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
    ConflictError: status.HTTP_409_CONFLICT,
}


@app.exception_handler(AgentForgeError)
async def agentforge_error_handler(_request: Request, exc: AgentForgeError) -> JSONResponse:
    status_code = _STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST)
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
async def health() -> dict[str, str]:
    """Liveness check used by Docker Compose and orchestrators."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}
