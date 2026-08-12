"""Run/RunStep/CostRecord persistence — stores execution results in Postgres."""

import uuid
from datetime import UTC, datetime
from typing import Any

from agentforge_common.enums import RunStatus, RunStepType
from agentforge_common.models import Run
from agentforge_common.orm import CostRecordORM, RunORM, RunStepORM
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _step_type(raw: str) -> RunStepType:
    return RunStepType(raw)


async def get_agent_spend_today(session: AsyncSession, agent_id: uuid.UUID) -> float:
    """Sum of CostRecord.cost_usd for this agent since midnight UTC."""
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.coalesce(func.sum(CostRecordORM.cost_usd), 0)).where(
            CostRecordORM.agent_id == agent_id,
            CostRecordORM.created_at >= start_of_day,
        )
    )
    return float(result.scalar_one())


async def create_run(
    session: AsyncSession,
    agent_id: uuid.UUID,
    agent_version: int,
    user_input: str,
) -> RunORM:
    """Create a pending Run row."""
    orm = RunORM(
        id=uuid.uuid4(),
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

    run_orm.output = output
    run_orm.status = status
    run_orm.trace_id = trace_id
    run_orm.started_at = run_orm.started_at or now
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
