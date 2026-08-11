"""Agent CRUD operations against Postgres — cursor pagination, no execution logic here."""

import base64
import json
import uuid
from datetime import datetime

from agentforge_common.exceptions import NotFoundError
from agentforge_common.models import Agent, AgentCreate, AgentUpdate
from agentforge_common.orm import AgentORM
from sqlalchemy import select, tuple_
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


async def create_agent(session: AsyncSession, payload: AgentCreate) -> Agent:
    orm = AgentORM(
        id=uuid.uuid4(),
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
    return _orm_to_model(orm)


async def list_agents(
    session: AsyncSession, limit: int, cursor: str | None
) -> tuple[list[Agent], str | None]:
    stmt = select(AgentORM).order_by(AgentORM.created_at.asc(), AgentORM.id.asc()).limit(limit + 1)
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


async def get_agent_orm(session: AsyncSession, agent_id: uuid.UUID) -> AgentORM:
    orm = await session.get(AgentORM, agent_id)
    if orm is None:
        raise NotFoundError("agent", str(agent_id))
    return orm


async def get_agent(session: AsyncSession, agent_id: uuid.UUID) -> Agent:
    return _orm_to_model(await get_agent_orm(session, agent_id))


async def update_agent(session: AsyncSession, agent_id: uuid.UUID, payload: AgentUpdate) -> Agent:
    orm = await get_agent_orm(session, agent_id)

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
    return _orm_to_model(orm)


async def delete_agent(session: AsyncSession, agent_id: uuid.UUID) -> None:
    orm = await get_agent_orm(session, agent_id)
    await session.delete(orm)
    await session.flush()
