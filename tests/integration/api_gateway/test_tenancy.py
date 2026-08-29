"""Integration tests for multi-tenant data isolation.

This is the concrete regression test for the leak migration 0003 closes:
before owner_id scoping, any valid API key could read/modify every agent,
run, eval suite, and cost record in the database regardless of who created
it. `api_key` (the default fixture) and `second_api_key` belong to two
distinct users — every test here confirms one user's calls never see or
touch the other's data.
"""

import uuid

import pytest
from agentforge_common.orm import ApiKeyORM, CostRecordORM
from sqlalchemy import select

AGENTS_BASE = "/api/v1/agents"
SUITES_BASE = "/api/v1/eval-suites"
KEYS_BASE = "/api/v1/api-keys"
ANALYTICS_BASE = "/api/v1/analytics"


def _agent_payload(name: str) -> dict:
    return {
        "name": name,
        "model": "gpt-4o-mini",
        "system_prompt": "Be helpful.",
    }


@pytest.mark.asyncio
async def test_agent_list_is_scoped_per_owner(client, api_key, second_api_key):
    await client.post(AGENTS_BASE, json=_agent_payload("a-agent"), headers={"X-API-Key": api_key})
    await client.post(
        AGENTS_BASE, json=_agent_payload("b-agent"), headers={"X-API-Key": second_api_key},
    )

    a_list = await client.get(AGENTS_BASE, headers={"X-API-Key": api_key})
    b_list = await client.get(AGENTS_BASE, headers={"X-API-Key": second_api_key})

    a_names = {a["name"] for a in a_list.json()["data"]}
    b_names = {a["name"] for a in b_list.json()["data"]}
    assert "a-agent" in a_names
    assert "b-agent" not in a_names
    assert "b-agent" in b_names
    assert "a-agent" not in b_names


@pytest.mark.asyncio
async def test_cannot_get_another_owners_agent(client, api_key, second_api_key):
    create_resp = await client.post(
        AGENTS_BASE, json=_agent_payload("private-agent"), headers={"X-API-Key": api_key},
    )
    agent_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"{AGENTS_BASE}/{agent_id}", headers={"X-API-Key": second_api_key})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_update_another_owners_agent(client, api_key, second_api_key):
    create_resp = await client.post(
        AGENTS_BASE, json=_agent_payload("private-agent"), headers={"X-API-Key": api_key},
    )
    agent_id = create_resp.json()["data"]["id"]

    resp = await client.put(
        f"{AGENTS_BASE}/{agent_id}",
        json={"status": "active"},
        headers={"X-API-Key": second_api_key},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_another_owners_agent(client, api_key, second_api_key):
    create_resp = await client.post(
        AGENTS_BASE, json=_agent_payload("private-agent"), headers={"X-API-Key": api_key},
    )
    agent_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"{AGENTS_BASE}/{agent_id}", headers={"X-API-Key": second_api_key})
    assert resp.status_code == 404

    # It's untouched — the owner can still see it.
    still_there = await client.get(f"{AGENTS_BASE}/{agent_id}", headers={"X-API-Key": api_key})
    assert still_there.status_code == 200


@pytest.mark.asyncio
async def test_cannot_clone_another_owners_agent(client, api_key, second_api_key):
    create_resp = await client.post(
        AGENTS_BASE, json=_agent_payload("private-agent"), headers={"X-API-Key": api_key},
    )
    agent_id = create_resp.json()["data"]["id"]

    resp = await client.post(
        f"{AGENTS_BASE}/{agent_id}/clone", headers={"X-API-Key": second_api_key},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_eval_suites_are_scoped_per_owner(client, api_key, second_api_key):
    agent_resp = await client.post(
        AGENTS_BASE, json=_agent_payload("eval-owner-agent"), headers={"X-API-Key": api_key},
    )
    agent_id = agent_resp.json()["data"]["id"]

    suite_resp = await client.post(
        SUITES_BASE,
        json={"name": "owner-suite", "agent_id": agent_id, "test_cases": []},
        headers={"X-API-Key": api_key},
    )
    suite_id = suite_resp.json()["data"]["id"]

    get_as_other = await client.get(
        f"{SUITES_BASE}/{suite_id}", headers={"X-API-Key": second_api_key},
    )
    assert get_as_other.status_code == 404

    list_as_other = await client.get(SUITES_BASE, headers={"X-API-Key": second_api_key})
    suite_ids = {s["id"] for s in list_as_other.json()["data"]}
    assert suite_id not in suite_ids


@pytest.mark.asyncio
async def test_analytics_do_not_leak_across_owners(client, api_key, second_api_key, session):
    a_agent = await client.post(
        AGENTS_BASE, json=_agent_payload("cost-agent-a"), headers={"X-API-Key": api_key},
    )
    b_agent = await client.post(
        AGENTS_BASE, json=_agent_payload("cost-agent-b"), headers={"X-API-Key": second_api_key},
    )

    a_owner = (
        await session.execute(select(ApiKeyORM.owner_id).where(ApiKeyORM.user_id == "test-user"))
    ).scalar_one()
    b_owner = (
        await session.execute(
            select(ApiKeyORM.owner_id).where(ApiKeyORM.user_id == "second-test-user")
        )
    ).scalar_one()

    session.add_all([
        CostRecordORM(
            id=uuid.uuid4(), owner_id=a_owner, agent_id=uuid.UUID(a_agent.json()["data"]["id"]),
            model="gpt-4o-mini", tokens_in=100, tokens_out=50, cost_usd=0.01,
        ),
        CostRecordORM(
            id=uuid.uuid4(), owner_id=b_owner, agent_id=uuid.UUID(b_agent.json()["data"]["id"]),
            model="gpt-4o-mini", tokens_in=999, tokens_out=999, cost_usd=99.0,
        ),
    ])
    await session.commit()

    a_usage = await client.get(f"{ANALYTICS_BASE}/usage", headers={"X-API-Key": api_key})
    a_data = a_usage.json()["data"]
    assert round(a_data["total_cost_usd"], 4) == 0.01
    assert a_data["total_calls"] == 1

    b_usage = await client.get(f"{ANALYTICS_BASE}/usage", headers={"X-API-Key": second_api_key})
    b_data = b_usage.json()["data"]
    assert b_data["total_cost_usd"] == 99.0
    assert b_data["total_calls"] == 1


@pytest.mark.asyncio
async def test_api_keys_are_scoped_per_owner(client, api_key, second_api_key):
    await client.post(KEYS_BASE, json={"user_id": "owner-a-extra"}, headers={"X-API-Key": api_key})
    await client.post(
        KEYS_BASE, json={"user_id": "owner-b-extra"}, headers={"X-API-Key": second_api_key},
    )

    a_keys = await client.get(KEYS_BASE, headers={"X-API-Key": api_key})
    b_keys = await client.get(KEYS_BASE, headers={"X-API-Key": second_api_key})

    a_labels = {k["user_id"] for k in a_keys.json()["data"]}
    b_labels = {k["user_id"] for k in b_keys.json()["data"]}
    assert "owner-a-extra" in a_labels
    assert "owner-b-extra" not in a_labels
    assert "owner-b-extra" in b_labels
    assert "owner-a-extra" not in b_labels
