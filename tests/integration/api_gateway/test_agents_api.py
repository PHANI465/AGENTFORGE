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


async def test_clone_agent_copies_config_with_new_id(client, api_key):
    headers = {"X-API-Key": api_key}
    create_resp = await client.post("/api/v1/agents", json=_agent_payload(), headers=headers)
    source = create_resp.json()["data"]

    clone_resp = await client.post(f"/api/v1/agents/{source['id']}/clone", headers=headers)
    assert clone_resp.status_code == 201
    cloned = clone_resp.json()["data"]

    assert cloned["id"] != source["id"]
    assert cloned["name"] == f"{source['name']} (copy)"
    assert cloned["model"] == source["model"]
    assert cloned["system_prompt"] == source["system_prompt"]
    assert cloned["tools"][0]["name"] == source["tools"][0]["name"]


async def test_clone_agent_with_custom_name(client, api_key):
    headers = {"X-API-Key": api_key}
    create_resp = await client.post("/api/v1/agents", json=_agent_payload(), headers=headers)
    source_id = create_resp.json()["data"]["id"]

    clone_resp = await client.post(
        f"/api/v1/agents/{source_id}/clone",
        json={"name": "staging-copy"},
        headers=headers,
    )
    assert clone_resp.status_code == 201
    assert clone_resp.json()["data"]["name"] == "staging-copy"


async def test_clone_nonexistent_agent_returns_404(client, api_key):
    headers = {"X-API-Key": api_key}
    response = await client.post(
        "/api/v1/agents/00000000-0000-0000-0000-000000000000/clone", headers=headers
    )
    assert response.status_code == 404


async def test_clone_starts_at_version_one(client, api_key):
    headers = {"X-API-Key": api_key}
    create_resp = await client.post("/api/v1/agents", json=_agent_payload(), headers=headers)
    source_id = create_resp.json()["data"]["id"]

    # Update the source so it accrues a second version — the clone should
    # not inherit this history.
    await client.put(
        f"/api/v1/agents/{source_id}", json={"status": "active"}, headers=headers
    )

    clone_resp = await client.post(f"/api/v1/agents/{source_id}/clone", headers=headers)
    cloned_id = clone_resp.json()["data"]["id"]

    versions_resp = await client.get(f"/api/v1/agents/{cloned_id}/versions", headers=headers)
    versions = versions_resp.json()["data"]
    assert len(versions) == 1
    assert versions[0]["version"] == 1


async def test_list_agents_filters_by_status(client, api_key):
    headers = {"X-API-Key": api_key}
    active_resp = await client.post(
        "/api/v1/agents", json=_agent_payload(name="active-agent"), headers=headers
    )
    await client.put(
        f"/api/v1/agents/{active_resp.json()['data']['id']}",
        json={"status": "active"},
        headers=headers,
    )
    await client.post("/api/v1/agents", json=_agent_payload(name="draft-agent"), headers=headers)

    resp = await client.get("/api/v1/agents", params={"status": "active"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert all(a["status"] == "active" for a in body["data"])
    assert any(a["name"] == "active-agent" for a in body["data"])
    assert not any(a["name"] == "draft-agent" for a in body["data"])


async def test_list_agents_search_is_case_insensitive_substring_match(client, api_key):
    headers = {"X-API-Key": api_key}
    await client.post(
        "/api/v1/agents", json=_agent_payload(name="Customer-Support-Bot"), headers=headers
    )
    await client.post("/api/v1/agents", json=_agent_payload(name="billing-agent"), headers=headers)

    resp = await client.get("/api/v1/agents", params={"search": "support"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    names = [a["name"] for a in body["data"]]
    assert "Customer-Support-Bot" in names
    assert "billing-agent" not in names


async def test_list_agents_reports_total_count_in_meta(client, api_key):
    headers = {"X-API-Key": api_key}
    for i in range(3):
        await client.post(
            "/api/v1/agents", json=_agent_payload(name=f"count-agent-{i}"), headers=headers
        )

    resp = await client.get(
        "/api/v1/agents", params={"limit": 1, "search": "count-agent"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] == 3
