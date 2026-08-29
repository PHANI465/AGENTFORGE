"""Shared FastAPI dependencies for the API Gateway: DB session + API key auth."""

import uuid
from collections.abc import AsyncGenerator

from agentforge_common.db import async_session_factory
from agentforge_common.exceptions import UnauthorizedError
from agentforge_common.orm import SYSTEM_USER_ID, ApiKeyORM
from agentforge_common.security import hash_api_key
from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def require_api_key(
    raw_key: str | None = Security(_api_key_header),
    session: AsyncSession = Depends(get_db),
) -> ApiKeyORM:
    """Resolves the `X-API-Key` header to its api_keys row, or raises 401.

    Route handlers scope every query by `auth.owner_id` — this is the single
    place that resolves who's calling. Keys minted before tenancy existed
    have `owner_id = NULL`; see docs/security.md for what that means.
    """
    if not raw_key:
        raise UnauthorizedError("Missing X-API-Key header")

    result = await session.execute(
        select(ApiKeyORM).where(ApiKeyORM.key_hash == hash_api_key(raw_key))
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise UnauthorizedError("Invalid API key")
    return api_key


def owner_id_of(auth: ApiKeyORM) -> uuid.UUID:
    """The tenant id every query should be scoped by for this caller.

    `api_keys.owner_id` is NOT NULL — every key created through the API
    already has a real owner_id (the system user for pre-tenancy/unclaimed
    keys, a real user once real accounts exist). This wrapper exists so
    callers never read `auth.owner_id` directly, and as a defensive fallback
    for any row that reached the DB by some other path than the API.
    """
    return auth.owner_id or SYSTEM_USER_ID
