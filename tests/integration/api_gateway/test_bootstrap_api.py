"""Integration tests for POST /api/v1/api-keys/bootstrap — the bridge
between auth-service's JWT and AgentForge's normal bearer-API-key model.

The real JWKS fetch (jwt_auth._refresh_jwks) is patched to avoid needing a
live auth-service: these tests sign tokens with a real RSA keypair
generated in-process and pre-populate jwt_auth's cache with its public
half directly, exercising the actual verification path in jwt_auth.py
(decode, signature check, issuer/claim checks) rather than mocking that
away too.
"""

import time
import uuid
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from agentforge_common.orm import SYSTEM_USER_ID
from cryptography.hazmat.primitives.asymmetric import rsa

BASE = "/api/v1/api-keys"
KID = "test-key-1"


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture(autouse=True)
def _patch_jwks_cache(rsa_keypair):
    """Pre-populates jwt_auth's module-level JWKS cache directly, and
    patches _refresh_jwks to a no-op so a stale/missing cache entry
    doesn't trigger a real HTTP call to a nonexistent auth-service."""
    _, public_key = rsa_keypair
    import jwt_auth

    jwt_auth._cached_keys.clear()
    jwt_auth._cached_keys[KID] = public_key
    jwt_auth._cache_fetched_at = time.monotonic()

    with patch("jwt_auth._refresh_jwks", new=AsyncMock(return_value=None)):
        yield

    jwt_auth._cached_keys.clear()
    jwt_auth._cache_fetched_at = 0.0


def _sign(
    private_key, *, sub: str, jti: str = "access", kid: str = KID,
    issuer: str = "agentforge-auth-service",
) -> str:
    now = int(time.time())
    claims = {
        "sub": sub, "email": "test@example.com", "iss": issuer,
        "jti": jti, "iat": now, "exp": now + 900,
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


@pytest.mark.asyncio
async def test_bootstrap_with_valid_token_mints_a_key(client, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _sign(private_key, sub=str(SYSTEM_USER_ID))

    resp = await client.post(f"{BASE}/bootstrap", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["raw_key"].startswith("afk_")
    assert data["user_id"] == "test@example.com"

    # The minted key actually authenticates and is scoped to the JWT's sub.
    list_resp = await client.get("/api/v1/agents", headers={"X-API-Key": data["raw_key"]})
    assert list_resp.status_code == 200


@pytest.mark.asyncio
async def test_bootstrap_without_authorization_header_is_401(client):
    resp = await client.post(f"{BASE}/bootstrap")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_with_malformed_token_is_401(client):
    resp = await client.post(f"{BASE}/bootstrap", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_with_wrong_signing_key_is_401(client, rsa_keypair):
    # Signed by a *different* key than the one jwt_auth has cached under
    # the same kid — must fail signature verification, not silently pass.
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _sign(other_key, sub=str(SYSTEM_USER_ID))

    resp = await client.post(f"{BASE}/bootstrap", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_with_refresh_token_is_rejected(client, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _sign(private_key, sub=str(SYSTEM_USER_ID), jti="refresh")

    resp = await client.post(f"{BASE}/bootstrap", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_with_wrong_issuer_is_401(client, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _sign(private_key, sub=str(SYSTEM_USER_ID), issuer="someone-else")

    resp = await client.post(f"{BASE}/bootstrap", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_for_unknown_user_is_401_not_a_crash(client, rsa_keypair):
    # A syntactically valid, correctly-signed token for a user that
    # doesn't exist in `users` — checked explicitly (not left to the FK
    # constraint) so this is a clean 401, not an unhandled IntegrityError.
    private_key, _ = rsa_keypair
    token = _sign(private_key, sub=str(uuid.uuid4()))

    resp = await client.post(f"{BASE}/bootstrap", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
