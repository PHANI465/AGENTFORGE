"""EvalRun/EvalResult persistence — stores scored eval results returned by the eval-service."""

import uuid
from datetime import UTC, datetime
from typing import Any

from agentforge_common.enums import EvalRunStatus
from agentforge_common.exceptions import NotFoundError
from agentforge_common.orm import EvalResultORM, EvalRunORM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_eval_run(
    session: AsyncSession, suite_id: uuid.UUID, agent_version: int
) -> EvalRunORM:
    orm = EvalRunORM(
        id=uuid.uuid4(),
        suite_id=suite_id,
        agent_version=agent_version,
        status=EvalRunStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    session.add(orm)
    await session.flush()
    return orm


async def complete_eval_run(
    session: AsyncSession,
    eval_run_orm: EvalRunORM,
    results: list[dict[str, Any]],
) -> EvalRunORM:
    """Persist EvalResult rows, compute a summary, and mark the run completed."""
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    avg_latency = int(sum(r.get("latency_ms", 0) for r in results) / total) if total else 0
    total_cost = sum(r.get("cost_usd", 0.0) for r in results)
    total_tokens = sum(r.get("tokens_used", 0) for r in results)

    for r in results:
        session.add(EvalResultORM(
            id=uuid.uuid4(),
            eval_run_id=eval_run_orm.id,
            test_case_id=r["test_case_id"],
            passed=r["passed"],
            score=r.get("score"),
            actual_output=r.get("actual_output"),
            latency_ms=r.get("latency_ms"),
            tokens_used=r.get("tokens_used"),
            safety_violations=r.get("safety_violations", []),
        ))

    eval_run_orm.status = EvalRunStatus.COMPLETED
    eval_run_orm.completed_at = datetime.now(UTC)
    eval_run_orm.summary = {
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": (passed_count / total) if total else 0.0,
        "avg_latency_ms": avg_latency,
        "total_cost_usd": total_cost,
        "total_tokens_used": total_tokens,
    }

    await session.flush()
    await session.refresh(eval_run_orm)
    return eval_run_orm


async def get_eval_run_orm(session: AsyncSession, eval_run_id: uuid.UUID) -> EvalRunORM:
    orm = await session.get(EvalRunORM, eval_run_id)
    if orm is None:
        raise NotFoundError("eval_run", str(eval_run_id))
    return orm


async def get_eval_results(session: AsyncSession, eval_run_id: uuid.UUID) -> list[EvalResultORM]:
    result = await session.execute(
        select(EvalResultORM).where(EvalResultORM.eval_run_id == eval_run_id)
    )
    return list(result.scalars().all())
