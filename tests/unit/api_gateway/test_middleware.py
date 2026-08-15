"""Unit tests for RequestIDMiddleware — exercised against a minimal Starlette
app rather than the full api-gateway app.py, so no DB/dependency wiring is
needed to test the middleware's own behavior."""

import sys
import uuid
from pathlib import Path

import structlog

API_GATEWAY_DIR = Path(__file__).resolve().parents[3] / "services" / "api-gateway"
if str(API_GATEWAY_DIR) not in sys.path:
    sys.path.append(str(API_GATEWAY_DIR))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from middleware import RequestIDMiddleware  # noqa: E402


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"request_id": structlog.contextvars.get_contextvars().get("request_id", "")}

    return app


class TestRequestIDMiddleware:
    def test_generates_request_id_when_absent(self) -> None:
        client = TestClient(_build_app())
        resp = client.get("/ping")
        assert "X-Request-ID" in resp.headers
        # Should be a valid UUID4 string.
        uuid.UUID(resp.headers["X-Request-ID"])

    def test_echoes_incoming_request_id(self) -> None:
        client = TestClient(_build_app())
        incoming = "my-custom-request-id"
        resp = client.get("/ping", headers={"X-Request-ID": incoming})
        assert resp.headers["X-Request-ID"] == incoming

    def test_request_id_bound_to_structlog_context_during_request(self) -> None:
        client = TestClient(_build_app())
        incoming = "bound-context-id"
        resp = client.get("/ping", headers={"X-Request-ID": incoming})
        assert resp.json()["request_id"] == incoming

    def test_each_request_gets_a_distinct_generated_id(self) -> None:
        client = TestClient(_build_app())
        first = client.get("/ping").headers["X-Request-ID"]
        second = client.get("/ping").headers["X-Request-ID"]
        assert first != second
