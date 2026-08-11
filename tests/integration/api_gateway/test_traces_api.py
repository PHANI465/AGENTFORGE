"""Integration tests for the trace endpoint: GET /api/v1/runs/{id}/trace.

Creates a run with mocked runtime response, then fetches its trace and
verifies the structured timeline and summary.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

BASE = "/api/v1/agents"
TRACE_BASE = "/api/v1/runs"


def _runtime_response_with_steps():
    return {
        "output": "The current time is 2026-08-11T12:00:00Z.",
        "steps": [
            {
                "step_number": 1,
                "type": "llm_call",
                "input": {"messages_count": 2},
                "output": {"content": None, "tool_calls_count": 1},
                "tokens_in": 50,
                "tokens_out": 20,
                "latency_ms": 300,
            },
            {
                "step_number": 2,
                "type": "tool_call",
                "input": {"tool_name": "get_current_time", "arguments": {}},
                "output": {"result": "2026-08-11T12:00:00Z"},
                "tokens_in": 0,
                "tokens_out": 0,
                "latency_ms": 5,
            },
            {
                "step_number": 3,
                "type": "llm_call",
                "input": {"messages_count": 4},
                "output": {"content": "The current time is 2026-08-11T12:00:00Z.",
                           "tool_calls_count": 0},
                "tokens_in": 60,
                "tokens_out": 15,
                "latency_ms": 250,
            },
        ],
        "total_tokens_in": 110,
        "total_tokens_out": 35,
        "total_cost_usd": 0.00005,
        "model": "gpt-4o-mini",
        "error": None,
        "trace_id": "abc123def456",
    }


def _mock_httpx_post(runtime_response: dict, status_code: int = 200):
    mock_resp = AsyncMock(spec=Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = runtime_response
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return patch("routers.runs.httpx.AsyncClient", return_value=mock_client)


async def _create_agent(client, api_key: str) -> dict:
    payload = {
        "name": "trace-test-agent",
        "model": "gpt-4o-mini",
        "system_prompt": "You are a helpful assistant.",
        "tools": [{"name": "get_current_time", "description": "Returns UTC time"}],
    }
    resp = await client.post(BASE, json=payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 201
    return resp.json()["data"]


async def _run_agent(client, agent_id: str, api_key: str) -> dict:
    with _mock_httpx_post(_runtime_response_with_steps()):
        resp = await client.post(
            f"{BASE}/{agent_id}/run",
            json={"input": "What time is it?"},
            headers={"X-API-Key": api_key},
        )
    assert resp.status_code == 200
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_get_trace_success(client, api_key):
    """Fetch a trace for a completed run — spans and summary are correct."""
    agent = await _create_agent(client, api_key)
    run = await _run_agent(client, agent["id"], api_key)

    resp = await client.get(
        f"{TRACE_BASE}/{run['id']}/trace",
        headers={"X-API-Key": api_key},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["run_id"] == run["id"]
    assert data["agent_id"] == agent["id"]
    assert data["trace_id"] == "abc123def456"
    assert data["status"] == "completed"

    assert len(data["spans"]) == 3
    assert data["spans"][0]["type"] == "llm_call"
    assert data["spans"][1]["type"] == "tool_call"
    assert data["spans"][2]["type"] == "llm_call"

    summary = data["summary"]
    assert summary["total_steps"] == 3
    assert summary["total_llm_calls"] == 2
    assert summary["total_tool_calls"] == 1
    assert summary["total_safety_checks"] == 0
    assert summary["total_tokens_in"] == 110
    assert summary["total_tokens_out"] == 35
    assert summary["total_latency_ms"] == 555


@pytest.mark.asyncio
async def test_get_trace_not_found(client, api_key):
    """404 when the run doesn't exist."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"{TRACE_BASE}/{fake_id}/trace",
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_trace_requires_auth(client):
    """401 without an API key."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{TRACE_BASE}/{fake_id}/trace")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_trace_includes_safety_steps(client, api_key):
    """Trace summary correctly counts safety_check steps."""
    agent_payload = {
        "name": "safety-trace-agent",
        "model": "gpt-4o-mini",
        "system_prompt": "You are a helpful assistant.",
        "tools": [],
        "safety_policy": {
            "rules": ["never share customer PII"],
            "on_violation": "warn",
        },
    }
    resp = await client.post(BASE, json=agent_payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 201
    agent = resp.json()["data"]

    runtime_resp = {
        "output": "Contact john@example.com for help.",
        "steps": [
            {
                "step_number": 1,
                "type": "llm_call",
                "input": {"messages_count": 2},
                "output": {"content": "Contact john@example.com for help.",
                           "tool_calls_count": 0},
                "tokens_in": 40,
                "tokens_out": 10,
                "latency_ms": 200,
            },
            {
                "step_number": 2,
                "type": "safety_check",
                "input": {"check_point": "post_llm", "content_length": 34},
                "output": {"passed": False,
                           "violations": [{"rule": "never share customer PII",
                                          "matched_text": "john@example.com",
                                          "pattern_name": "email_address",
                                          "check_point": "post_llm"}],
                           "action": "warn"},
                "tokens_in": 0,
                "tokens_out": 0,
                "latency_ms": 0,
            },
        ],
        "total_tokens_in": 40,
        "total_tokens_out": 10,
        "total_cost_usd": 0.00001,
        "model": "gpt-4o-mini",
        "error": None,
        "trace_id": "safety-trace-001",
    }

    with _mock_httpx_post(runtime_resp):
        run_resp = await client.post(
            f"{BASE}/{agent['id']}/run",
            json={"input": "What is John's email?"},
            headers={"X-API-Key": api_key},
        )
    assert run_resp.status_code == 200
    run = run_resp.json()["data"]

    trace_resp = await client.get(
        f"{TRACE_BASE}/{run['id']}/trace",
        headers={"X-API-Key": api_key},
    )
    assert trace_resp.status_code == 200
    summary = trace_resp.json()["data"]["summary"]
    assert summary["total_safety_checks"] == 1
    assert summary["total_llm_calls"] == 1
