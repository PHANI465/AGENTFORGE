"""API key management — POST/GET /api/v1/api-keys.

The dashboard's Settings page needs a self-serve way to mint keys; until now
the only way was running scripts/seed.py by hand. Creating a key requires an
existing valid key (bootstrap still happens via the seed script or an admin
running it once), matching the auth model everywhere else in the platform.
"""

import uuid
from datetime import datetime

from agentforge_common.envelope import DataResponse, ListMeta, ListResponse
from agentforge_common.orm import ApiKeyORM
from agentforge_common.security import generate_api_key, hash_api_key
from dependencies import get_db, require_api_key
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


class ApiKeyCreate(BaseModel):
    user_id: str
    provider: str = "openai"


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    user_id: str
    provider: str
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    """Only returned once, at creation time — the raw key is never stored or shown again."""

    raw_key: str


@router.post("", response_model=DataResponse[ApiKeyCreated], status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[ApiKeyCreated]:
    raw_key = generate_api_key()
    orm = ApiKeyORM(
        id=uuid.uuid4(),
        key_hash=hash_api_key(raw_key),
        user_id=payload.user_id,
        provider=payload.provider,
        encrypted_key="",
    )
    session.add(orm)
    await session.flush()
    await session.refresh(orm)

    return DataResponse(data=ApiKeyCreated(
        id=orm.id, user_id=orm.user_id, provider=orm.provider,
        created_at=orm.created_at, raw_key=raw_key,
    ))


@router.get("", response_model=ListResponse[ApiKeyOut])
async def list_api_keys(
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> ListResponse[ApiKeyOut]:
    result = await session.execute(select(ApiKeyORM).order_by(ApiKeyORM.created_at.desc()))
    rows = list(result.scalars().all())
    return ListResponse(
        data=[ApiKeyOut(id=r.id, user_id=r.user_id, provider=r.provider, created_at=r.created_at)
              for r in rows],
        meta=ListMeta(next_cursor=None, limit=len(rows)),
    )
