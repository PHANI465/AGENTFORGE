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


@pytest.mark.asyncio
async def test_delete_api_key_revokes_it(client, api_key):
    create_resp = await client.post(
        BASE, json={"user_id": "throwaway-user"}, headers={"X-API-Key": api_key},
    )
    created = create_resp.json()["data"]

    delete_resp = await client.delete(
        f"{BASE}/{created['id']}", headers={"X-API-Key": api_key},
    )
    assert delete_resp.status_code == 204

    # The revoked key can no longer authenticate.
    auth_resp = await client.get("/api/v1/agents", headers={"X-API-Key": created["raw_key"]})
    assert auth_resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_api_key_removes_it_from_list(client, api_key):
    create_resp = await client.post(
        BASE, json={"user_id": "to-be-removed"}, headers={"X-API-Key": api_key},
    )
    created_id = create_resp.json()["data"]["id"]

    await client.delete(f"{BASE}/{created_id}", headers={"X-API-Key": api_key})

    list_resp = await client.get(BASE, headers={"X-API-Key": api_key})
    remaining_ids = {row["id"] for row in list_resp.json()["data"]}
    assert created_id not in remaining_ids


@pytest.mark.asyncio
async def test_cannot_revoke_the_authenticating_key(client, api_key):
    # api_key is the only key in the DB for this test, so it is both "self"
    # and the last remaining key — either guard alone would 409 this.
    list_resp = await client.get(BASE, headers={"X-API-Key": api_key})
    self_id = list_resp.json()["data"][0]["id"]

    resp = await client.delete(f"{BASE}/{self_id}", headers={"X-API-Key": api_key})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


@pytest.mark.asyncio
async def test_can_delete_down_to_one_key_remaining(client, api_key):
    # Three keys total (api_key + two created here). Deleting non-self keys
    # down to a single survivor should never be blocked — the API's
    # "last remaining key" guard only matters once you'd be revoking your
    # own authenticating key, which test_cannot_revoke_the_authenticating_key
    # covers; with the current single-tenant auth model there's no way to
    # be authenticated as anything other than the one surviving key once
    # total == 1, so that branch is unreachable independent of self-auth.
    second_resp = await client.post(
        BASE, json={"user_id": "second-user"}, headers={"X-API-Key": api_key},
    )
    third_resp = await client.post(
        BASE, json={"user_id": "third-user"}, headers={"X-API-Key": api_key},
    )
    second_id = second_resp.json()["data"]["id"]
    third_key = third_resp.json()["data"]["raw_key"]
    third_id = third_resp.json()["data"]["id"]

    list_resp = await client.get(BASE, headers={"X-API-Key": third_key})
    first_id = next(
        row["id"] for row in list_resp.json()["data"]
        if row["id"] not in (second_id, third_id)
    )

    delete_first = await client.delete(f"{BASE}/{first_id}", headers={"X-API-Key": third_key})
    assert delete_first.status_code == 204

    delete_second = await client.delete(f"{BASE}/{second_id}", headers={"X-API-Key": third_key})
    assert delete_second.status_code == 204

    list_final = await client.get(BASE, headers={"X-API-Key": third_key})
    assert len(list_final.json()["data"]) == 1


@pytest.mark.asyncio
async def test_delete_nonexistent_api_key_returns_404(client, api_key):
    resp = await client.delete(
        f"{BASE}/00000000-0000-0000-0000-000000000000", headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_api_key_requires_auth(client, api_key):
    create_resp = await client.post(
        BASE, json={"user_id": "needs-auth-to-delete"}, headers={"X-API-Key": api_key},
    )
    created_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"{BASE}/{created_id}")
    assert resp.status_code == 401
