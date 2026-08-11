"""Eval suite CRUD against Postgres — cursor pagination, mirrors crud_agents.py."""

import base64
import json
import uuid
from datetime import datetime

from agentforge_common.exceptions import NotFoundError
from agentforge_common.models import EvalSuite, EvalSuiteCreate
from agentforge_common.orm import EvalSuiteORM
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession


def _orm_to_model(orm: EvalSuiteORM) -> EvalSuite:
    return EvalSuite(
        id=orm.id,
        name=orm.name,
        agent_id=orm.agent_id,
        test_cases=orm.test_cases,
        created_at=orm.created_at,
    )


def _encode_cursor(created_at: datetime, suite_id: uuid.UUID) -> str:
    raw = json.dumps({"created_at": created_at.isoformat(), "id": str(suite_id)})
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    payload = json.loads(raw)
    return datetime.fromisoformat(payload["created_at"]), uuid.UUID(payload["id"])


async def create_eval_suite(session: AsyncSession, payload: EvalSuiteCreate) -> EvalSuite:
    orm = EvalSuiteORM(
        id=uuid.uuid4(),
        name=payload.name,
        agent_id=payload.agent_id,
        test_cases=[tc.model_dump() for tc in payload.test_cases],
    )
    session.add(orm)
    await session.flush()
    await session.refresh(orm)
    return _orm_to_model(orm)


async def list_eval_suites(
    session: AsyncSession, limit: int, cursor: str | None
) -> tuple[list[EvalSuite], str | None]:
    stmt = (
        select(EvalSuiteORM)
        .order_by(EvalSuiteORM.created_at.asc(), EvalSuiteORM.id.asc())
        .limit(limit + 1)
    )
    if cursor:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(EvalSuiteORM.created_at, EvalSuiteORM.id) > (cursor_created_at, cursor_id)
        )

    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return [_orm_to_model(row) for row in rows], next_cursor


async def get_eval_suite_orm(session: AsyncSession, suite_id: uuid.UUID) -> EvalSuiteORM:
    orm = await session.get(EvalSuiteORM, suite_id)
    if orm is None:
        raise NotFoundError("eval_suite", str(suite_id))
    return orm


async def get_eval_suite(session: AsyncSession, suite_id: uuid.UUID) -> EvalSuite:
    return _orm_to_model(await get_eval_suite_orm(session, suite_id))
