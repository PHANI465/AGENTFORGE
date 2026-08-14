"""Middleware for the API Gateway."""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request ID to every request.

    - Reads an existing X-Request-ID header (e.g., from a load balancer), or
      generates a new UUID4.
    - Binds it to structlog's context vars so every log line in the request
      includes `request_id`.
    - Returns it in the response's X-Request-ID header so callers can
      correlate.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
