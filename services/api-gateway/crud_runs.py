"""Run/RunStep/CostRecord persistence — stores execution results in Postgres."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from agentforge_common.enums import RunStatus, RunStepType
from agentforge_common.models import Run
from agentforge_common.orm import CostRecordORM, RunORM, RunStepORM
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _step_type(raw: str) -> RunStepType:
    return RunStepType(raw)


async def count_runs_for_agent(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID
) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(RunORM)
        .where(RunORM.agent_id == agent_id, RunORM.owner_id == owner_id)
    )
    return result.scalar_one()


async def list_runs_for_agent(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID, limit: int = 20
) -> list[Run]:
    """Most recent runs for an agent, newest first. Runs that never started
    (e.g. crashed before completion) sort last since started_at is null."""
    result = await session.execute(
        select(RunORM)
        .where(RunORM.agent_id == agent_id, RunORM.owner_id == owner_id)
        .order_by(desc(RunORM.started_at).nulls_last())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        Run(
            id=r.id, agent_id=r.agent_id, agent_version=r.agent_version,
            input=r.input, output=r.output, status=r.status, trace_id=r.trace_id,
            started_at=r.started_at, completed_at=r.completed_at,
        )
        for r in rows
    ]


async def get_agent_spend_today(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID
) -> float:
    """Sum of CostRecord.cost_usd for this agent since midnight UTC."""
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.coalesce(func.sum(CostRecordORM.cost_usd), 0)).where(
            CostRecordORM.agent_id == agent_id,
            CostRecordORM.owner_id == owner_id,
            CostRecordORM.created_at >= start_of_day,
        )
    )
    return float(result.scalar_one())


async def create_run(
    session: AsyncSession,
    owner_id: uuid.UUID,
    agent_id: uuid.UUID,
    agent_version: int,
    user_input: str,
) -> RunORM:
    """Create a pending Run row."""
    orm = RunORM(
        id=uuid.uuid4(),
        owner_id=owner_id,
        agent_id=agent_id,
        agent_version=agent_version,
        input=user_input,
        status=RunStatus.PENDING,
    )
    session.add(orm)
    await session.flush()
    return orm


async def complete_run(
    session: AsyncSession,
    run_orm: RunORM,
    output: str,
    status: RunStatus,
    steps_data: list[dict[str, Any]],
    model: str,
    total_tokens_in: int,
    total_tokens_out: int,
    total_cost_usd: float,
    trace_id: str | None = None,
) -> Run:
    """Finalise a Run with its output, steps, and cost record."""
    now = datetime.now(UTC)

    started = run_orm.started_at
    if started is None:
        # Guard against clock resolution coarser than the gap between
        # sequential run completions for the same agent (observed on this
        # platform: datetime.now(UTC) can return an identical value across
        # several rapid successive calls) — without this, "list recent runs,
        # newest first" isn't reliably ordered when runs complete in a tight
        # loop. Bumping by a microsecond keeps started_at strictly
        # increasing per agent without needing a schema-level tiebreaker.
        last_started = await session.scalar(
            select(func.max(RunORM.started_at)).where(RunORM.agent_id == run_orm.agent_id)
        )
        started = now
        if last_started is not None and started <= last_started:
            started = last_started + timedelta(microseconds=1)

    run_orm.output = output
    run_orm.status = status
    run_orm.trace_id = trace_id
    run_orm.started_at = started
    run_orm.completed_at = now

    for step in steps_data:
        session.add(RunStepORM(
            id=uuid.uuid4(),
            run_id=run_orm.id,
            step_number=step["step_number"],
            type=_step_type(step["type"]),
            input=step.get("input", {}),
            output=step.get("output", {}),
            tokens_in=step.get("tokens_in"),
            tokens_out=step.get("tokens_out"),
            latency_ms=step.get("latency_ms"),
        ))

    if total_tokens_in or total_tokens_out:
        session.add(CostRecordORM(
            id=uuid.uuid4(),
            owner_id=run_orm.owner_id,
            agent_id=run_orm.agent_id,
            run_id=run_orm.id,
            model=model,
            tokens_in=total_tokens_in,
            tokens_out=total_tokens_out,
            cost_usd=total_cost_usd,
        ))

    await session.flush()
    await session.refresh(run_orm)

    return Run(
        id=run_orm.id,
        agent_id=run_orm.agent_id,
        agent_version=run_orm.agent_version,
        input=run_orm.input,
        output=run_orm.output,
        status=run_orm.status,
        trace_id=run_orm.trace_id,
        started_at=run_orm.started_at,
        completed_at=run_orm.completed_at,
    )
