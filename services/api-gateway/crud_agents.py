"""Agent CRUD operations against Postgres — cursor pagination, no execution logic here.

Every query here is scoped by `owner_id`: a caller can only see/modify agents
they own. An agent that exists but belongs to someone else raises the same
NotFoundError as one that doesn't exist at all — that's deliberate, so a
caller can't distinguish "not found" from "not yours" by probing IDs.
"""

import base64
import json
import uuid
from datetime import datetime

from agentforge_common.exceptions import NotFoundError
from agentforge_common.models import Agent, AgentCreate, AgentUpdate
from agentforge_common.orm import AgentORM, AgentVersionORM
from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession


def _orm_to_model(orm: AgentORM) -> Agent:
    return Agent(
        id=orm.id,
        name=orm.name,
        model=orm.model,
        system_prompt=orm.system_prompt,
        tools=orm.tools_config,
        safety_policy=orm.safety_policy,
        config=orm.config,
        status=orm.status,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _encode_cursor(created_at: datetime, agent_id: uuid.UUID) -> str:
    raw = json.dumps({"created_at": created_at.isoformat(), "id": str(agent_id)})
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    payload = json.loads(raw)
    return datetime.fromisoformat(payload["created_at"]), uuid.UUID(payload["id"])


def _snapshot(orm: AgentORM) -> dict:
    return {
        "name": orm.name,
        "model": orm.model,
        "system_prompt": orm.system_prompt,
        "tools_config": orm.tools_config,
        "safety_policy": orm.safety_policy,
        "config": orm.config,
        "status": orm.status.value if hasattr(orm.status, "value") else str(orm.status),
    }


async def _next_version(session: AsyncSession, agent_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(AgentVersionORM.version), 0)).where(
            AgentVersionORM.agent_id == agent_id
        )
    )
    return result.scalar_one() + 1


async def count_agents(
    session: AsyncSession,
    owner_id: uuid.UUID,
    status_filter: str | None = None,
    search: str | None = None,
) -> int:
    stmt = select(func.count()).select_from(AgentORM).where(AgentORM.owner_id == owner_id)
    if status_filter:
        stmt = stmt.where(AgentORM.status == status_filter)
    if search:
        stmt = stmt.where(AgentORM.name.ilike(f"%{search}%"))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_agent(session: AsyncSession, owner_id: uuid.UUID, payload: AgentCreate) -> Agent:
    orm = AgentORM(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name=payload.name,
        model=payload.model,
        system_prompt=payload.system_prompt,
        tools_config=[tool.model_dump() for tool in payload.tools],
        safety_policy=payload.safety_policy.model_dump(),
        config=payload.config.model_dump(),
    )
    session.add(orm)
    await session.flush()
    await session.refresh(orm)

    session.add(AgentVersionORM(
        id=uuid.uuid4(), agent_id=orm.id, version=1, snapshot=_snapshot(orm),
    ))
    await session.flush()

    return _orm_to_model(orm)


async def list_agents(
    session: AsyncSession,
    owner_id: uuid.UUID,
    limit: int,
    cursor: str | None,
    status_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[Agent], str | None]:
    stmt = (
        select(AgentORM)
        .where(AgentORM.owner_id == owner_id)
        .order_by(AgentORM.created_at.asc(), AgentORM.id.asc())
        .limit(limit + 1)
    )
    if status_filter:
        stmt = stmt.where(AgentORM.status == status_filter)
    if search:
        stmt = stmt.where(AgentORM.name.ilike(f"%{search}%"))
    if cursor:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(AgentORM.created_at, AgentORM.id) > (cursor_created_at, cursor_id)
        )

    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return [_orm_to_model(row) for row in rows], next_cursor


async def get_agent_orm(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID
) -> AgentORM:
    result = await session.execute(
        select(AgentORM).where(AgentORM.id == agent_id, AgentORM.owner_id == owner_id)
    )
    orm = result.scalar_one_or_none()
    if orm is None:
        raise NotFoundError("agent", str(agent_id))
    return orm


async def get_agent(session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID) -> Agent:
    return _orm_to_model(await get_agent_orm(session, owner_id, agent_id))


async def update_agent(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID, payload: AgentUpdate
) -> Agent:
    orm = await get_agent_orm(session, owner_id, agent_id)

    updates = payload.model_dump(exclude_unset=True)
    if "tools" in updates:
        orm.tools_config = updates.pop("tools")
    if "safety_policy" in updates:
        orm.safety_policy = updates.pop("safety_policy")
    if "config" in updates:
        orm.config = updates.pop("config")
    for field, value in updates.items():
        setattr(orm, field, value)

    await session.flush()
    await session.refresh(orm)

    new_version = await _next_version(session, agent_id)
    session.add(AgentVersionORM(
        id=uuid.uuid4(), agent_id=agent_id, version=new_version, snapshot=_snapshot(orm),
    ))
    await session.flush()

    return _orm_to_model(orm)


async def list_versions(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID
) -> list[AgentVersionORM]:
    await get_agent_orm(session, owner_id, agent_id)
    result = await session.execute(
        select(AgentVersionORM)
        .where(AgentVersionORM.agent_id == agent_id)
        .order_by(AgentVersionORM.version.desc())
    )
    return list(result.scalars().all())


async def rollback_agent(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID, target_version: int
) -> Agent:
    await get_agent_orm(session, owner_id, agent_id)
    result = await session.execute(
        select(AgentVersionORM).where(
            AgentVersionORM.agent_id == agent_id,
            AgentVersionORM.version == target_version,
        )
    )
    version_orm = result.scalar_one_or_none()
    if version_orm is None:
        raise NotFoundError("agent_version", f"{agent_id}@v{target_version}")

    snap = version_orm.snapshot
    orm = await get_agent_orm(session, owner_id, agent_id)
    orm.name = snap["name"]
    orm.model = snap["model"]
    orm.system_prompt = snap["system_prompt"]
    orm.tools_config = snap["tools_config"]
    orm.safety_policy = snap["safety_policy"]
    orm.config = snap["config"]

    await session.flush()
    await session.refresh(orm)

    new_version = await _next_version(session, agent_id)
    session.add(AgentVersionORM(
        id=uuid.uuid4(), agent_id=agent_id, version=new_version, snapshot=_snapshot(orm),
    ))
    await session.flush()

    return _orm_to_model(orm)


async def clone_agent(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID, new_name: str | None = None
) -> Agent:
    source = await get_agent_orm(session, owner_id, agent_id)
    orm = AgentORM(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name=new_name or f"{source.name} (copy)",
        model=source.model,
        system_prompt=source.system_prompt,
        tools_config=source.tools_config,
        safety_policy=source.safety_policy,
        config=source.config,
    )
    session.add(orm)
    await session.flush()
    await session.refresh(orm)

    session.add(AgentVersionORM(
        id=uuid.uuid4(), agent_id=orm.id, version=1, snapshot=_snapshot(orm),
    ))
    await session.flush()

    return _orm_to_model(orm)


async def delete_agent(session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID) -> None:
    orm = await get_agent_orm(session, owner_id, agent_id)
    await session.delete(orm)
    await session.flush()
