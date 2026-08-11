"""Integration tests for /api/v1/agents against a real Postgres test database."""



def _agent_payload(name: str = "support-agent") -> dict:
    return {
        "name": name,
        "model": "gpt-4o-mini",
        "system_prompt": "Be helpful.",
        "tools": [
            {
                "name": "get_weather",
                "description": "Get current weather",
                "parameters_schema": {"type": "object"},
            }
        ],
        "safety_policy": {"rules": ["never share PII"], "on_violation": "block"},
        "config": {"max_tokens": 512},
    }


async def test_create_agent_requires_api_key(client):
    response = await client.post("/api/v1/agents", json=_agent_payload())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_create_agent_rejects_invalid_api_key(client):
    response = await client.post(
        "/api/v1/agents", json=_agent_payload(), headers={"X-API-Key": "not-a-real-key"}
    )
    assert response.status_code == 401


async def test_create_and_get_agent(client, api_key):
    headers = {"X-API-Key": api_key}

    create_resp = await client.post("/api/v1/agents", json=_agent_payload(), headers=headers)
    assert create_resp.status_code == 201
    created = create_resp.json()["data"]
    assert created["name"] == "support-agent"
    assert created["status"] == "draft"
    assert created["tools"][0]["name"] == "get_weather"

    get_resp = await client.get(f"/api/v1/agents/{created['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == created["id"]


async def test_get_nonexistent_agent_returns_404(client, api_key):
    headers = {"X-API-Key": api_key}
    response = await client.get(
        "/api/v1/agents/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_list_agents_paginates(client, api_key):
    headers = {"X-API-Key": api_key}
    for i in range(5):
        resp = await client.post(
            "/api/v1/agents", json=_agent_payload(name=f"agent-{i}"), headers=headers
        )
        assert resp.status_code == 201

    page1 = await client.get("/api/v1/agents", params={"limit": 2}, headers=headers)
    assert page1.status_code == 200
    body1 = page1.json()
    assert len(body1["data"]) == 2
    assert body1["meta"]["next_cursor"] is not None

    page2 = await client.get(
        "/api/v1/agents",
        params={"limit": 2, "cursor": body1["meta"]["next_cursor"]},
        headers=headers,
    )
    assert page2.status_code == 200
    body2 = page2.json()
    assert len(body2["data"]) == 2

    page1_ids = {a["id"] for a in body1["data"]}
    page2_ids = {a["id"] for a in body2["data"]}
    assert page1_ids.isdisjoint(page2_ids)


async def test_update_agent_partial(client, api_key):
    headers = {"X-API-Key": api_key}
    create_resp = await client.post("/api/v1/agents", json=_agent_payload(), headers=headers)
    agent_id = create_resp.json()["data"]["id"]

    update_resp = await client.put(
        f"/api/v1/agents/{agent_id}",
        json={"status": "active", "system_prompt": "Be extra helpful."},
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()["data"]
    assert updated["status"] == "active"
    assert updated["system_prompt"] == "Be extra helpful."
    assert updated["name"] == "support-agent"  # untouched fields survive


async def test_update_nonexistent_agent_returns_404(client, api_key):
    headers = {"X-API-Key": api_key}
    response = await client.put(
        "/api/v1/agents/00000000-0000-0000-0000-000000000000",
        json={"status": "active"},
        headers=headers,
    )
    assert response.status_code == 404


async def test_delete_agent(client, api_key):
    headers = {"X-API-Key": api_key}
    create_resp = await client.post("/api/v1/agents", json=_agent_payload(), headers=headers)
    agent_id = create_resp.json()["data"]["id"]

    delete_resp = await client.delete(f"/api/v1/agents/{agent_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/agents/{agent_id}", headers=headers)
    assert get_resp.status_code == 404
