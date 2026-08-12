"""Integration tests for POST/GET /api/v1/api-keys."""

import pytest

BASE = "/api/v1/api-keys"


@pytest.mark.asyncio
async def test_create_api_key_returns_raw_key_once(client, api_key):
    resp = await client.post(
        BASE, json={"user_id": "new-user", "provider": "openai"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["user_id"] == "new-user"
    assert data["provider"] == "openai"
    assert data["raw_key"].startswith("afk_")


@pytest.mark.asyncio
async def test_created_key_can_authenticate(client, api_key):
    create_resp = await client.post(
        BASE, json={"user_id": "second-user"}, headers={"X-API-Key": api_key},
    )
    new_key = create_resp.json()["data"]["raw_key"]

    list_resp = await client.get("/api/v1/agents", headers={"X-API-Key": new_key})
    assert list_resp.status_code == 200


@pytest.mark.asyncio
async def test_list_api_keys_excludes_raw_key(client, api_key):
    await client.post(BASE, json={"user_id": "listed-user"}, headers={"X-API-Key": api_key})

    resp = await client.get(BASE, headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert len(rows) >= 1
    assert "raw_key" not in rows[0]
    assert "key_hash" not in rows[0]


@pytest.mark.asyncio
async def test_create_api_key_requires_auth(client):
    resp = await client.post(BASE, json={"user_id": "nobody"})
    assert resp.status_code == 401
