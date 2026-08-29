"""Verifies session JWTs issued by services/auth-service (Phase 3.3).

Deliberately narrow: only the bootstrap endpoint in routers/api_keys.py
uses this. Every other route still only ever sees `X-API-Key` — this
exists purely to let a freshly logged-in dashboard user (who has a JWT
proving who they are, but no AgentForge API key yet) mint their first key,
closing the loop between auth-service's identity and api-gateway's
existing bearer-token auth model without retrofitting every route.

The public key is fetched from auth-service's JWKS endpoint and cached —
api-gateway never sees or needs the private signing key.
"""

import base64
import os
import time

import httpx
import jwt
from agentforge_common.exceptions import UnauthorizedError
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPublicNumbers

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8004")
_JWKS_CACHE_TTL_SECONDS = 3600

_cached_keys: dict[str, RSAPublicKey] = {}
_cache_fetched_at: float = 0.0


def _b64url_to_int(value: str) -> int:
    padded = value + "=" * (-len(value) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(padded), "big")


def _jwk_to_public_key(jwk: dict) -> RSAPublicKey:
    n = _b64url_to_int(jwk["n"])
    e = _b64url_to_int(jwk["e"])
    return RSAPublicNumbers(e, n).public_key()


async def _refresh_jwks() -> None:
    global _cache_fetched_at
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{AUTH_SERVICE_URL}/.well-known/jwks.json")
        resp.raise_for_status()
        jwks = resp.json()

    _cached_keys.clear()
    for jwk in jwks.get("keys", []):
        kid = jwk.get("kid")
        if kid:
            _cached_keys[kid] = _jwk_to_public_key(jwk)
    _cache_fetched_at = time.monotonic()


async def _get_public_key(kid: str) -> RSAPublicKey:
    stale = time.monotonic() - _cache_fetched_at > _JWKS_CACHE_TTL_SECONDS
    if kid not in _cached_keys or stale:
        try:
            await _refresh_jwks()
        except httpx.HTTPError as e:
            raise UnauthorizedError(f"Could not reach auth service to verify token: {e}") from e
    try:
        return _cached_keys[kid]
    except KeyError:
        raise UnauthorizedError(
            "Unknown signing key — token was not issued by this platform"
        ) from None


async def verify_session_jwt(token: str) -> dict:
    """Returns the token's claims (sub, email, ...) or raises UnauthorizedError."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError(f"Malformed token: {e}") from e

    kid = header.get("kid")
    if not kid:
        raise UnauthorizedError("Token is missing a key ID")

    public_key = await _get_public_key(kid)

    try:
        claims = jwt.decode(
            token, public_key, algorithms=["RS256"],
            issuer="agentforge-auth-service", options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError(f"Invalid or expired token: {e}") from e

    if claims.get("jti") != "access":
        raise UnauthorizedError("This endpoint requires an access token, not a refresh token")

    return claims
