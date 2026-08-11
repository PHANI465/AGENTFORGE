"""Shared FastAPI dependencies for the API Gateway: DB session + API key auth."""

from collections.abc import AsyncGenerator

from agentforge_common.db import async_session_factory
from agentforge_common.exceptions import UnauthorizedError
from agentforge_common.orm import ApiKeyORM
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
    """Resolves the `X-API-Key` header to its api_keys row, or raises 401."""
    if not raw_key:
        raise UnauthorizedError("Missing X-API-Key header")

    result = await session.execute(
        select(ApiKeyORM).where(ApiKeyORM.key_hash == hash_api_key(raw_key))
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise UnauthorizedError("Invalid API key")
    return api_key
