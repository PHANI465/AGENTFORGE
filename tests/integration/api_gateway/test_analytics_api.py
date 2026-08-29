"""Integration tests for GET /api/v1/analytics/costs and /usage."""

import uuid

import pytest
from agentforge_common.orm import SYSTEM_USER_ID, CostRecordORM

BASE = "/api/v1/agents"
ANALYTICS_BASE = "/api/v1/analytics"


async def _create_agent(client, api_key: str) -> dict:
    payload = {
        "name": "analytics-test-agent",
        "model": "gpt-4o-mini",
        "system_prompt": "You are a helpful assistant.",
    }
    resp = await client.post(BASE, json=payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 201
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_usage_summary_aggregates_cost_records(client, api_key, session):
    agent = await _create_agent(client, api_key)
    agent_id = uuid.UUID(agent["id"])

    session.add_all([
        CostRecordORM(id=uuid.uuid4(), owner_id=SYSTEM_USER_ID, agent_id=agent_id,
                       model="gpt-4o-mini", tokens_in=100, tokens_out=50, cost_usd=0.01),
        CostRecordORM(id=uuid.uuid4(), owner_id=SYSTEM_USER_ID, agent_id=agent_id,
                       model="gpt-4o-mini", tokens_in=200, tokens_out=80, cost_usd=0.02),
    ])
    await session.commit()

    resp = await client.get(
        f"{ANALYTICS_BASE}/usage", params={"agent_id": str(agent_id)},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_calls"] == 2
    assert round(data["total_cost_usd"], 4) == 0.03
    assert data["total_tokens_in"] == 300
    assert data["total_tokens_out"] == 130
    assert round(data["avg_cost_per_call_usd"], 4) == 0.015


@pytest.mark.asyncio
async def test_usage_summary_empty_when_no_records(client, api_key):
    resp = await client.get(f"{ANALYTICS_BASE}/usage", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_calls"] == 0
    assert data["total_cost_usd"] == 0.0
    assert data["avg_cost_per_call_usd"] == 0.0


@pytest.mark.asyncio
async def test_cost_breakdown_scoped_to_agent(client, api_key, session):
    agent_a = await _create_agent(client, api_key)
    agent_b = await _create_agent(client, api_key)

    session.add_all([
        CostRecordORM(id=uuid.uuid4(), owner_id=SYSTEM_USER_ID, agent_id=uuid.UUID(agent_a["id"]),
                       model="gpt-4o-mini", tokens_in=100, tokens_out=50, cost_usd=0.01),
        CostRecordORM(id=uuid.uuid4(), owner_id=SYSTEM_USER_ID, agent_id=uuid.UUID(agent_b["id"]),
                       model="gpt-4o-mini", tokens_in=100, tokens_out=50, cost_usd=0.05),
    ])
    await session.commit()

    resp = await client.get(
        f"{ANALYTICS_BASE}/costs", params={"agent_id": agent_a["id"]},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert len(rows) == 1
    assert rows[0]["agent_id"] == agent_a["id"]
    assert round(rows[0]["total_cost_usd"], 4) == 0.01
    assert rows[0]["call_count"] == 1


@pytest.mark.asyncio
async def test_analytics_requires_auth(client):
    resp = await client.get(f"{ANALYTICS_BASE}/usage")
    assert resp.status_code == 401
