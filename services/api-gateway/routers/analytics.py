"""Cost/usage analytics — GET /api/v1/analytics/costs, GET /api/v1/analytics/usage.

Aggregates CostRecord rows written by every completed run. This is the "cost
comparison" surface for Milestone 7: since caching/routing/compression all
change how much a given workload costs, these numbers are what makes that
difference visible over time (pair with the Grafana cache-hit-rate panel for
the live operational view).
"""

import uuid
from datetime import UTC, datetime, timedelta

from agentforge_common.envelope import DataResponse
from agentforge_common.orm import ApiKeyORM, CostRecordORM
from dependencies import get_db, require_api_key
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class CostBreakdownRow(BaseModel):
    date: str
    agent_id: uuid.UUID
    total_cost_usd: float
    total_tokens_in: int
    total_tokens_out: int
    call_count: int


class UsageSummary(BaseModel):
    window_days: int
    total_calls: int
    total_cost_usd: float
    total_tokens_in: int
    total_tokens_out: int
    avg_cost_per_call_usd: float


@router.get(
    "/costs",
    response_model=DataResponse[list[CostBreakdownRow]],
    summary="Daily cost breakdown",
    operation_id="getCostBreakdown",
)
async def cost_breakdown(
    agent_id: uuid.UUID | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[list[CostBreakdownRow]]:
    """Daily cost/token breakdown, optionally scoped to one agent."""
    since = datetime.now(UTC) - timedelta(days=days)

    day_col = func.date(CostRecordORM.created_at)
    stmt = (
        select(
            day_col.label("day"),
            CostRecordORM.agent_id,
            func.sum(CostRecordORM.cost_usd).label("total_cost_usd"),
            func.sum(CostRecordORM.tokens_in).label("total_tokens_in"),
            func.sum(CostRecordORM.tokens_out).label("total_tokens_out"),
            func.count().label("call_count"),
        )
        .where(CostRecordORM.created_at >= since)
        .group_by(day_col, CostRecordORM.agent_id)
        .order_by(day_col)
    )
    if agent_id is not None:
        stmt = stmt.where(CostRecordORM.agent_id == agent_id)

    rows = (await session.execute(stmt)).all()

    return DataResponse(data=[
        CostBreakdownRow(
            date=str(r.day),
            agent_id=r.agent_id,
            total_cost_usd=float(r.total_cost_usd or 0),
            total_tokens_in=int(r.total_tokens_in or 0),
            total_tokens_out=int(r.total_tokens_out or 0),
            call_count=int(r.call_count or 0),
        )
        for r in rows
    ])


@router.get(
    "/usage",
    response_model=DataResponse[UsageSummary],
    summary="Aggregate usage summary",
    operation_id="getUsageSummary",
)
async def usage_summary(
    agent_id: uuid.UUID | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[UsageSummary]:
    """Aggregate token/cost/call totals over a window, optionally scoped to one agent."""
    since = datetime.now(UTC) - timedelta(days=days)

    stmt = select(
        func.coalesce(func.sum(CostRecordORM.cost_usd), 0).label("total_cost_usd"),
        func.coalesce(func.sum(CostRecordORM.tokens_in), 0).label("total_tokens_in"),
        func.coalesce(func.sum(CostRecordORM.tokens_out), 0).label("total_tokens_out"),
        func.count().label("total_calls"),
    ).where(CostRecordORM.created_at >= since)
    if agent_id is not None:
        stmt = stmt.where(CostRecordORM.agent_id == agent_id)

    row = (await session.execute(stmt)).one()
    total_calls = int(row.total_calls or 0)
    total_cost = float(row.total_cost_usd or 0)

    return DataResponse(data=UsageSummary(
        window_days=days,
        total_calls=total_calls,
        total_cost_usd=total_cost,
        total_tokens_in=int(row.total_tokens_in or 0),
        total_tokens_out=int(row.total_tokens_out or 0),
        avg_cost_per_call_usd=(total_cost / total_calls) if total_calls else 0.0,
    ))
