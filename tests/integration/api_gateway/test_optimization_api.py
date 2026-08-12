"""Integration tests for Milestone 7: budget enforcement and optimization-config passthrough."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from agentforge_common.orm import CostRecordORM
from httpx import Response

BASE = "/api/v1/agents"


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


def _clean_runtime_response() -> dict:
    return {
        "output": "Hello!",
        "steps": [{"step_number": 1, "type": "llm_call",
                    "input": {"messages_count": 2},
                    "output": {"content": "Hello!", "tool_calls_count": 0},
                    "tokens_in": 10, "tokens_out": 5, "latency_ms": 100}],
        "total_tokens_in": 10, "total_tokens_out": 5,
        "total_cost_usd": 0.000005, "model": "gpt-4o-mini", "error": None,
        "trace_id": "abc123",
    }


async def _create_agent(client, api_key: str, daily_budget_usd: float | None = None) -> dict:
    payload = {
        "name": "budget-test-agent",
        "model": "gpt-4o-mini",
        "system_prompt": "You are a helpful assistant.",
        "tools": [],
        "config": {
            "max_tokens": 1024, "temperature": 0.7, "timeout": 30,
            "optimization": {"daily_budget_usd": daily_budget_usd},
        },
    }
    resp = await client.post(BASE, json=payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 201
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_run_proceeds_when_no_budget_set(client, api_key):
    agent = await _create_agent(client, api_key, daily_budget_usd=None)

    with _mock_httpx_post(_clean_runtime_response()):
        resp = await client.post(
            f"{BASE}/{agent['id']}/run", json={"input": "hi"},
            headers={"X-API-Key": api_key},
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_run_proceeds_when_under_budget(client, api_key, session):
    agent = await _create_agent(client, api_key, daily_budget_usd=10.0)
    session.add(CostRecordORM(
        id=uuid.uuid4(), agent_id=uuid.UUID(agent["id"]), model="gpt-4o-mini",
        tokens_in=100, tokens_out=50, cost_usd=0.01,
    ))
    await session.commit()

    with _mock_httpx_post(_clean_runtime_response()):
        resp = await client.post(
            f"{BASE}/{agent['id']}/run", json={"input": "hi"},
            headers={"X-API-Key": api_key},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_run_rejected_when_budget_exceeded(client, api_key, session):
    agent = await _create_agent(client, api_key, daily_budget_usd=0.005)
    session.add(CostRecordORM(
        id=uuid.uuid4(), agent_id=uuid.UUID(agent["id"]), model="gpt-4o-mini",
        tokens_in=1000, tokens_out=500, cost_usd=0.01,
    ))
    await session.commit()

    resp = await client.post(
        f"{BASE}/{agent['id']}/run", json={"input": "hi"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "budget_exceeded"


@pytest.mark.asyncio
async def test_optimization_config_sent_to_runtime(client, api_key):
    payload = {
        "name": "routing-test-agent",
        "model": "gpt-4o",
        "system_prompt": "You are a helpful assistant.",
        "tools": [],
        "config": {
            "optimization": {
                "enable_caching": True,
                "enable_smart_routing": True,
                "simple_model": "gpt-4o-mini",
                "complex_model": "gpt-4o",
                "complexity_threshold": 150,
                "enable_compression": True,
                "compression_threshold_chars": 1500,
            }
        },
    }
    resp = await client.post(BASE, json=payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 201
    agent = resp.json()["data"]

    with _mock_httpx_post(_clean_runtime_response()) as mock_cls:
        run_resp = await client.post(
            f"{BASE}/{agent['id']}/run", json={"input": "hi"},
            headers={"X-API-Key": api_key},
        )
    assert run_resp.status_code == 200

    mock_instance = mock_cls.return_value
    call_args = mock_instance.post.call_args
    sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
    opt = sent_payload["optimization"]
    assert opt["enable_smart_routing"] is True
    assert opt["simple_model"] == "gpt-4o-mini"
    assert opt["complex_model"] == "gpt-4o"
    assert opt["enable_compression"] is True
    assert opt["compression_threshold_chars"] == 1500
