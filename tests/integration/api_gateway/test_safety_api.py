"""Integration tests for safety policy enforcement through the full pipeline.

Mock the agent-runtime HTTP call with responses that contain PII or blocked
keywords, and verify the run status and step records reflect the safety outcome.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

BASE = "/api/v1/agents"


def _runtime_response_with_pii():
    """Simulates a runtime response where the LLM leaked PII and safety blocked it."""
    return {
        "output": "[BLOCKED] Response violated safety policy and was not delivered.",
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
                "output": {
                    "passed": False,
                    "violations": [
                        {"rule": "never share customer PII",
                         "matched_text": "john@example.com",
                         "pattern_name": "email_address",
                         "check_point": "post_llm"}
                    ],
                    "action": "block",
                },
                "tokens_in": 0,
                "tokens_out": 0,
                "latency_ms": 0,
            },
        ],
        "total_tokens_in": 40,
        "total_tokens_out": 10,
        "total_cost_usd": 0.00001,
        "model": "gpt-4o-mini",
        "error": "Safety policy violation: response blocked",
    }


def _runtime_response_with_warn():
    """Simulates a runtime response where safety warned but continued."""
    return {
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
                "output": {
                    "passed": False,
                    "violations": [
                        {"rule": "never share customer PII",
                         "matched_text": "john@example.com",
                         "pattern_name": "email_address",
                         "check_point": "post_llm"}
                    ],
                    "action": "warn",
                },
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


async def _create_agent_with_safety(client, api_key: str, on_violation: str = "block") -> dict:
    payload = {
        "name": "safety-test-agent",
        "model": "gpt-4o-mini",
        "system_prompt": "You are a helpful assistant.",
        "tools": [],
        "safety_policy": {
            "rules": ["never share customer PII"],
            "on_violation": on_violation,
        },
    }
    resp = await client.post(BASE, json=payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 201
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_block_mode_marks_run_failed(client, api_key):
    """Agent with block mode: PII in LLM response → run status 'failed'."""
    agent = await _create_agent_with_safety(client, api_key, on_violation="block")

    with _mock_httpx_post(_runtime_response_with_pii()):
        resp = await client.post(
            f"{BASE}/{agent['id']}/run",
            json={"input": "What is John's email?"},
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert data["output"] == "[BLOCKED] Response violated safety policy and was not delivered."


@pytest.mark.asyncio
async def test_block_mode_persists_safety_check_step(client, api_key, session):
    """Verify the safety_check step is written to the DB."""
    from agentforge_common.orm import RunStepORM
    from sqlalchemy import select

    agent = await _create_agent_with_safety(client, api_key, on_violation="block")

    with _mock_httpx_post(_runtime_response_with_pii()):
        resp = await client.post(
            f"{BASE}/{agent['id']}/run",
            json={"input": "What is John's email?"},
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 200
    run_id = uuid.UUID(resp.json()["data"]["id"])

    result = await session.execute(
        select(RunStepORM).where(RunStepORM.run_id == run_id)
        .order_by(RunStepORM.step_number)
    )
    steps = result.scalars().all()
    assert len(steps) == 2
    assert steps[1].type.value == "safety_check"
    assert steps[1].output["passed"] is False
    assert steps[1].output["action"] == "block"
    assert steps[1].output["violations"][0]["pattern_name"] == "email_address"


@pytest.mark.asyncio
async def test_warn_mode_completes_with_output(client, api_key):
    """Agent with warn mode: PII detected, but run completes with the output."""
    agent = await _create_agent_with_safety(client, api_key, on_violation="warn")

    with _mock_httpx_post(_runtime_response_with_warn()):
        resp = await client.post(
            f"{BASE}/{agent['id']}/run",
            json={"input": "What is John's email?"},
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "completed"
    assert "john@example.com" in data["output"]


@pytest.mark.asyncio
async def test_safety_payload_sent_to_runtime(client, api_key):
    """Verify the API Gateway passes safety_rules and on_violation to the runtime."""
    agent = await _create_agent_with_safety(client, api_key, on_violation="block")

    clean_response = {
        "output": "The weather is sunny.",
        "steps": [{"step_number": 1, "type": "llm_call",
                    "input": {"messages_count": 2},
                    "output": {"content": "The weather is sunny.",
                               "tool_calls_count": 0},
                    "tokens_in": 20, "tokens_out": 5, "latency_ms": 100}],
        "total_tokens_in": 20, "total_tokens_out": 5,
        "total_cost_usd": 0.000005, "model": "gpt-4o-mini", "error": None,
    }

    with _mock_httpx_post(clean_response) as mock_cls:
        resp = await client.post(
            f"{BASE}/{agent['id']}/run",
            json={"input": "What is the weather?"},
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 200
    mock_instance = mock_cls.return_value
    call_args = mock_instance.post.call_args
    sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
    assert sent_payload["safety_rules"] == ["never share customer PII"]
    assert sent_payload["on_violation"] == "block"
