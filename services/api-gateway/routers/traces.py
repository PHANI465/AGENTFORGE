"""Trace routes — GET /api/v1/runs/{id}/trace.

Returns a structured trace timeline for a completed run, built from
the persisted RunStep records.
"""

import uuid

from agentforge_common.envelope import DataResponse
from agentforge_common.exceptions import NotFoundError
from agentforge_common.orm import ApiKeyORM, RunORM, RunStepORM
from dependencies import get_db, require_api_key
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/runs", tags=["traces"])


class TraceSpan(BaseModel):
    step_number: int
    type: str
    input: dict
    output: dict
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None


class TraceSummary(BaseModel):
    total_steps: int
    total_llm_calls: int
    total_tool_calls: int
    total_safety_checks: int
    total_tokens_in: int
    total_tokens_out: int
    total_latency_ms: int


class TraceResponse(BaseModel):
    run_id: uuid.UUID
    agent_id: uuid.UUID
    trace_id: str | None = None
    status: str
    input: str
    output: str | None = None
    spans: list[TraceSpan] = Field(default_factory=list)
    summary: TraceSummary


@router.get(
    "/{run_id}/trace",
    response_model=DataResponse[TraceResponse],
    summary="Get execution trace for a run",
    operation_id="getRunTrace",
)
async def get_run_trace(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[TraceResponse]:
    """Return a structured trace for a run, built from its RunStep records."""
    run = await session.get(RunORM, run_id)
    if not run:
        raise NotFoundError("Run", str(run_id))

    result = await session.execute(
        select(RunStepORM)
        .where(RunStepORM.run_id == run_id)
        .order_by(RunStepORM.step_number)
    )
    step_rows = result.scalars().all()

    spans = [
        TraceSpan(
            step_number=s.step_number,
            type=s.type.value,
            input=s.input,
            output=s.output,
            tokens_in=s.tokens_in,
            tokens_out=s.tokens_out,
            latency_ms=s.latency_ms,
        )
        for s in step_rows
    ]

    llm_calls = [s for s in step_rows if s.type.value == "llm_call"]
    tool_calls = [s for s in step_rows if s.type.value == "tool_call"]
    safety_checks = [s for s in step_rows if s.type.value == "safety_check"]

    summary = TraceSummary(
        total_steps=len(step_rows),
        total_llm_calls=len(llm_calls),
        total_tool_calls=len(tool_calls),
        total_safety_checks=len(safety_checks),
        total_tokens_in=sum(s.tokens_in or 0 for s in step_rows),
        total_tokens_out=sum(s.tokens_out or 0 for s in step_rows),
        total_latency_ms=sum(s.latency_ms or 0 for s in step_rows),
    )

    trace_resp = TraceResponse(
        run_id=run.id,
        agent_id=run.agent_id,
        trace_id=run.trace_id,
        status=run.status.value,
        input=run.input,
        output=run.output,
        spans=spans,
        summary=summary,
    )

    return DataResponse(data=trace_resp)
