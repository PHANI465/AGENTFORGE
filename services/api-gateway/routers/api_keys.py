"""API key management — POST/GET/DELETE /api/v1/api-keys.

The dashboard's Settings page needs a self-serve way to mint and revoke keys.
Creating a key requires an existing valid key (bootstrap happens via
scripts/seed.py), matching the auth model everywhere else in the platform.
A new key inherits the creating caller's owner_id — this is "mint yourself
another key," not "mint a key for someone else"; a real signup flow that
creates new owners is the Go auth service's job (see MILESTONES.md).
"""

import uuid
from datetime import datetime

from agentforge_common.envelope import DataResponse, ListMeta, ListResponse
from agentforge_common.exceptions import ConflictError, NotFoundError
from agentforge_common.orm import ApiKeyORM
from agentforge_common.security import encrypt_key, generate_api_key, hash_api_key
from dependencies import get_db, owner_id_of, require_api_key
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


class ApiKeyCreate(BaseModel):
    user_id: str
    provider: str = "openai"
    llm_api_key: str = ""


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    user_id: str
    provider: str
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    """Only returned once, at creation time — the raw key is never stored or shown again."""

    raw_key: str


@router.post(
    "",
    response_model=DataResponse[ApiKeyCreated],
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key",
    operation_id="createApiKey",
)
async def create_api_key(
    payload: ApiKeyCreate,
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[ApiKeyCreated]:
    raw_key = generate_api_key()
    orm = ApiKeyORM(
        id=uuid.uuid4(),
        key_hash=hash_api_key(raw_key),
        user_id=payload.user_id,
        owner_id=owner_id_of(auth),
        provider=payload.provider,
        encrypted_key=encrypt_key(payload.llm_api_key),
    )
    session.add(orm)
    await session.flush()
    await session.refresh(orm)

    return DataResponse(data=ApiKeyCreated(
        id=orm.id, user_id=orm.user_id, provider=orm.provider,
        created_at=orm.created_at, raw_key=raw_key,
    ))


@router.get(
    "",
    response_model=ListResponse[ApiKeyOut],
    summary="List API keys",
    operation_id="listApiKeys",
)
async def list_api_keys(
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> ListResponse[ApiKeyOut]:
    result = await session.execute(
        select(ApiKeyORM)
        .where(ApiKeyORM.owner_id == owner_id_of(auth))
        .order_by(ApiKeyORM.created_at.desc())
    )
    rows = list(result.scalars().all())
    return ListResponse(
        data=[ApiKeyOut(id=r.id, user_id=r.user_id, provider=r.provider, created_at=r.created_at)
              for r in rows],
        meta=ListMeta(next_cursor=None, limit=len(rows)),
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
    operation_id="deleteApiKey",
)
async def delete_api_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> None:
    if auth.id == key_id:
        raise ConflictError("Cannot revoke the key used to authenticate this request")
    owner_id = owner_id_of(auth)
    result = await session.execute(
        select(ApiKeyORM).where(ApiKeyORM.id == key_id, ApiKeyORM.owner_id == owner_id)
    )
    orm = result.scalar_one_or_none()
    if orm is None:
        raise NotFoundError("api_key", str(key_id))
    total = (
        await session.execute(
            select(func.count()).select_from(ApiKeyORM).where(ApiKeyORM.owner_id == owner_id)
        )
    ).scalar_one()
    if total <= 1:
        raise ConflictError("Cannot revoke the last remaining API key")
    await session.delete(orm)
    await session.flush()
