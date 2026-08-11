"""Integration tests for POST /api/v1/agents/{id}/run.

Mock the agent-runtime HTTP call (we don't want real LLM calls), but test
everything else end-to-end: auth, agent lookup, Run/RunStep/CostRecord
persistence in the real Postgres test database.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

BASE = "/api/v1/agents"

FAKE_RUNTIME_RESPONSE = {
    "output": "The current time is 2026-08-10 12:00:00 UTC.",
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
            "output": {"result": "2026-08-10 12:00:00 UTC"},
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 1,
        },
        {
            "step_number": 3,
            "type": "llm_call",
            "input": {"messages_count": 4},
            "output": {"content": "The current time is 2026-08-10 12:00:00 UTC.",
                       "tool_calls_count": 0},
            "tokens_in": 80,
            "tokens_out": 15,
            "latency_ms": 250,
        },
    ],
    "total_tokens_in": 130,
    "total_tokens_out": 35,
    "total_cost_usd": 0.000025,
    "model": "gpt-4o-mini",
    "error": None,
}


def _mock_httpx_post(runtime_response: dict | None = None, status_code: int = 200):
    """Patch httpx.AsyncClient.post to return a canned runtime response."""
    resp_data = runtime_response or FAKE_RUNTIME_RESPONSE
    mock_resp = AsyncMock(spec=Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = resp_data
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return patch("routers.runs.httpx.AsyncClient", return_value=mock_client)


async def _create_agent(client, api_key: str) -> dict:
    """Helper: create an agent and return its data dict."""
    payload = {
        "name": "test-runner-agent",
        "model": "gpt-4o-mini",
        "system_prompt": "You are a helpful assistant.",
        "tools": [
            {
                "name": "get_current_time",
                "description": "Returns the current UTC time.",
                "parameters_schema": {"type": "object", "properties": {}, "required": []},
            },
        ],
        "config": {"max_tokens": 256, "temperature": 0.5, "timeout": 30},
    }
    resp = await client.post(
        f"{BASE}", json=payload, headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 201
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_run_agent_success(client, api_key):
    agent = await _create_agent(client, api_key)
    agent_id = agent["id"]

    with _mock_httpx_post():
        resp = await client.post(
            f"{BASE}/{agent_id}/run",
            json={"input": "What time is it?"},
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["agent_id"] == agent_id
    assert data["input"] == "What time is it?"
    assert data["output"] == "The current time is 2026-08-10 12:00:00 UTC."
    assert data["status"] == "completed"
    assert data["started_at"] is not None
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_run_requires_auth(client):
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"{BASE}/{fake_id}/run", json={"input": "hi"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_run_agent_not_found(client, api_key):
    fake_id = str(uuid.uuid4())
    with _mock_httpx_post():
        resp = await client.post(
            f"{BASE}/{fake_id}/run",
            json={"input": "hi"},
            headers={"X-API-Key": api_key},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_missing_input(client, api_key):
    agent = await _create_agent(client, api_key)
    with _mock_httpx_post():
        resp = await client.post(
            f"{BASE}/{agent['id']}/run",
            json={},
            headers={"X-API-Key": api_key},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_run_persists_steps_and_cost(client, api_key, session):
    """Verify that RunStep and CostRecord rows are written to the DB."""
    from agentforge_common.orm import CostRecordORM, RunStepORM
    from sqlalchemy import select

    agent = await _create_agent(client, api_key)

    with _mock_httpx_post():
        resp = await client.post(
            f"{BASE}/{agent['id']}/run",
            json={"input": "What time is it?"},
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 200
    run_id = uuid.UUID(resp.json()["data"]["id"])

    result = await session.execute(
        select(RunStepORM).where(RunStepORM.run_id == run_id)
        .order_by(RunStepORM.step_number)
    )
    steps = result.scalars().all()
    assert len(steps) == 3
    assert steps[0].type.value == "llm_call"
    assert steps[1].type.value == "tool_call"
    assert steps[2].type.value == "llm_call"
    assert steps[0].tokens_in == 50

    cost_result = await session.execute(
        select(CostRecordORM).where(CostRecordORM.run_id == run_id)
    )
    cost = cost_result.scalar_one()
    assert cost.tokens_in == 130
    assert cost.tokens_out == 35
    assert float(cost.cost_usd) == pytest.approx(0.000025, abs=1e-8)


@pytest.mark.asyncio
async def test_run_runtime_error_marks_failed(client, api_key):
    """When the runtime returns an error field, the Run status should be 'failed'."""
    agent = await _create_agent(client, api_key)

    error_response = {
        "output": "",
        "steps": [],
        "total_tokens_in": 10,
        "total_tokens_out": 0,
        "total_cost_usd": 0.0,
        "model": "gpt-4o-mini",
        "error": "Execution timed out after 30s",
    }

    with _mock_httpx_post(runtime_response=error_response):
        resp = await client.post(
            f"{BASE}/{agent['id']}/run",
            json={"input": "slow query"},
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
