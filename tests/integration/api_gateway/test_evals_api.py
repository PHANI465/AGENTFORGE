"""Integration tests for the eval pipeline: suite CRUD, running a suite, and comparing runs.

Mocks the eval-service HTTP call (`routers.evals.httpx.AsyncClient`) the same way
test_runs_api.py mocks the agent-runtime call.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

AGENTS_BASE = "/api/v1/agents"
SUITES_BASE = "/api/v1/eval-suites"
RUNS_BASE = "/api/v1/eval-runs"


def _mock_eval_service_post(eval_service_response: dict, status_code: int = 200):
    mock_resp = AsyncMock(spec=Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = eval_service_response
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return patch("routers.evals.httpx.AsyncClient", return_value=mock_client)


async def _create_agent(client, api_key: str) -> dict:
    payload = {
        "name": "eval-test-agent",
        "model": "gpt-4o-mini",
        "system_prompt": "You are a helpful assistant.",
        "tools": [{"name": "get_current_time", "description": "Returns UTC time"}],
    }
    resp = await client.post(AGENTS_BASE, json=payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 201
    return resp.json()["data"]


async def _create_suite(client, api_key: str, agent_id: str) -> dict:
    payload = {
        "name": "smoke-suite",
        "agent_id": agent_id,
        "test_cases": [
            {"id": "tc-1", "input": "What time is it?",
             "expected_output": None, "expected_tool_calls": ["get_current_time"], "tags": []},
            {"id": "tc-2", "input": "Say hello.",
             "expected_output": "A friendly greeting", "expected_tool_calls": [], "tags": []},
        ],
    }
    resp = await client.post(SUITES_BASE, json=payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 201
    return resp.json()["data"]


def _sample_eval_results() -> dict:
    return {
        "results": [
            {"test_case_id": "tc-1", "passed": True, "score": 1.0,
             "actual_output": "It's noon.", "latency_ms": 200, "tokens_used": 40,
             "cost_usd": 0.00002, "safety_violations": [], "error": None},
            {"test_case_id": "tc-2", "passed": True, "score": 0.9,
             "actual_output": "Hello there!", "latency_ms": 150, "tokens_used": 20,
             "cost_usd": 0.00001, "safety_violations": [], "error": None},
        ]
    }


@pytest.mark.asyncio
async def test_create_list_get_eval_suite(client, api_key):
    agent = await _create_agent(client, api_key)
    suite = await _create_suite(client, api_key, agent["id"])

    assert suite["name"] == "smoke-suite"
    assert suite["agent_id"] == agent["id"]
    assert len(suite["test_cases"]) == 2

    list_resp = await client.get(SUITES_BASE, headers={"X-API-Key": api_key})
    assert list_resp.status_code == 200
    assert any(s["id"] == suite["id"] for s in list_resp.json()["data"])

    get_resp = await client.get(f"{SUITES_BASE}/{suite['id']}", headers={"X-API-Key": api_key})
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == suite["id"]


@pytest.mark.asyncio
async def test_get_nonexistent_suite_returns_404(client, api_key):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{SUITES_BASE}/{fake_id}", headers={"X-API-Key": api_key})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_suite_requires_auth(client):
    resp = await client.post(SUITES_BASE, json={"name": "x", "agent_id": str(uuid.uuid4()),
                                                  "test_cases": []})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_run_eval_suite_success(client, api_key):
    agent = await _create_agent(client, api_key)
    suite = await _create_suite(client, api_key, agent["id"])

    with _mock_eval_service_post(_sample_eval_results()):
        resp = await client.post(
            f"{SUITES_BASE}/{suite['id']}/run", headers={"X-API-Key": api_key}
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "completed"
    assert data["summary"]["total"] == 2
    assert data["summary"]["passed"] == 2
    assert data["summary"]["pass_rate"] == 1.0
    assert len(data["results"]) == 2
    result_ids = {r["test_case_id"] for r in data["results"]}
    assert result_ids == {"tc-1", "tc-2"}


@pytest.mark.asyncio
async def test_run_eval_suite_sends_agent_config_to_eval_service(client, api_key):
    agent = await _create_agent(client, api_key)
    suite = await _create_suite(client, api_key, agent["id"])

    with _mock_eval_service_post(_sample_eval_results()) as mock_cls:
        resp = await client.post(
            f"{SUITES_BASE}/{suite['id']}/run", headers={"X-API-Key": api_key}
        )

    assert resp.status_code == 200
    mock_instance = mock_cls.return_value
    call_args = mock_instance.post.call_args
    sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
    assert sent_payload["agent"]["model"] == "gpt-4o-mini"
    assert sent_payload["agent"]["tool_names"] == ["get_current_time"]
    assert len(sent_payload["test_cases"]) == 2


@pytest.mark.asyncio
async def test_get_eval_run(client, api_key):
    agent = await _create_agent(client, api_key)
    suite = await _create_suite(client, api_key, agent["id"])

    with _mock_eval_service_post(_sample_eval_results()):
        run_resp = await client.post(
            f"{SUITES_BASE}/{suite['id']}/run", headers={"X-API-Key": api_key}
        )
    run_id = run_resp.json()["data"]["id"]

    resp = await client.get(f"{RUNS_BASE}/{run_id}", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == run_id
    assert len(resp.json()["data"]["results"]) == 2


@pytest.mark.asyncio
async def test_compare_eval_runs(client, api_key):
    agent = await _create_agent(client, api_key)
    suite = await _create_suite(client, api_key, agent["id"])

    with _mock_eval_service_post(_sample_eval_results()):
        run_a_resp = await client.post(
            f"{SUITES_BASE}/{suite['id']}/run", headers={"X-API-Key": api_key}
        )
    run_a_id = run_a_resp.json()["data"]["id"]

    worse_results = {
        "results": [
            {"test_case_id": "tc-1", "passed": False, "score": 0.2,
             "actual_output": "I don't know.", "latency_ms": 900, "tokens_used": 60,
             "cost_usd": 0.00005, "safety_violations": [], "error": None},
            {"test_case_id": "tc-2", "passed": True, "score": 0.8,
             "actual_output": "Hi.", "latency_ms": 300, "tokens_used": 25,
             "cost_usd": 0.00002, "safety_violations": [], "error": None},
        ]
    }
    with _mock_eval_service_post(worse_results):
        run_b_resp = await client.post(
            f"{SUITES_BASE}/{suite['id']}/run", headers={"X-API-Key": api_key}
        )
    run_b_id = run_b_resp.json()["data"]["id"]

    resp = await client.get(
        f"{RUNS_BASE}/{run_a_id}/compare/{run_b_id}", headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_a"]["id"] == run_a_id
    assert data["run_b"]["id"] == run_b_id
    assert data["pass_rate_delta"] == -0.5
    assert data["avg_latency_ms_delta"] > 0


@pytest.mark.asyncio
async def test_list_eval_runs_for_suite(client, api_key):
    agent = await _create_agent(client, api_key)
    suite = await _create_suite(client, api_key, agent["id"])

    with _mock_eval_service_post(_sample_eval_results()):
        await client.post(f"{SUITES_BASE}/{suite['id']}/run", headers={"X-API-Key": api_key})
        await client.post(f"{SUITES_BASE}/{suite['id']}/run", headers={"X-API-Key": api_key})

    resp = await client.get(f"{SUITES_BASE}/{suite['id']}/runs", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    runs = resp.json()["data"]
    assert len(runs) == 2
    assert all(r["suite_id"] == suite["id"] for r in runs)
    assert all(r["results"] == [] for r in runs)


@pytest.mark.asyncio
async def test_list_eval_runs_empty_for_new_suite(client, api_key):
    agent = await _create_agent(client, api_key)
    suite = await _create_suite(client, api_key, agent["id"])

    resp = await client.get(f"{SUITES_BASE}/{suite['id']}/runs", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    assert resp.json()["data"] == []
