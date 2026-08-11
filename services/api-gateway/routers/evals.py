"""Eval routes — suite CRUD, running a suite against an agent, and comparing results.

POST /api/v1/eval-suites             — create a suite
GET  /api/v1/eval-suites             — list suites
GET  /api/v1/eval-suites/{id}        — get a suite
POST /api/v1/eval-suites/{id}/run    — execute the suite's test cases against its agent
GET  /api/v1/eval-runs/{id}          — get a completed eval run with its results
GET  /api/v1/eval-runs/{id}/compare/{other_id} — compare two eval runs
"""

import os
import uuid
from datetime import datetime
from typing import Any

import crud_agents
import crud_eval_runs
import crud_evals
import httpx
from agentforge_common.envelope import DataResponse, ListMeta, ListResponse
from agentforge_common.exceptions import AgentForgeError
from agentforge_common.models import EvalSuite, EvalSuiteCreate
from agentforge_common.orm import ApiKeyORM, EvalResultORM, EvalRunORM
from dependencies import get_db, require_api_key
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["eval"])

EVAL_SERVICE_URL = os.getenv("EVAL_SERVICE_URL", "http://localhost:8002")


class EvalServiceError(AgentForgeError):
    code = "eval_service_error"


class EvalResultOut(BaseModel):
    test_case_id: str
    passed: bool
    score: float | None = None
    actual_output: str | None = None
    latency_ms: int | None = None
    tokens_used: int | None = None
    safety_violations: list[dict[str, Any]] = Field(default_factory=list)


class EvalRunOut(BaseModel):
    id: uuid.UUID
    suite_id: uuid.UUID
    agent_version: int
    status: str
    summary: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    results: list[EvalResultOut] = Field(default_factory=list)


class EvalCompareOut(BaseModel):
    run_a: EvalRunOut
    run_b: EvalRunOut
    pass_rate_delta: float | None = None
    avg_latency_ms_delta: int | None = None
    total_cost_usd_delta: float | None = None


def _result_orm_to_out(orm: EvalResultORM) -> EvalResultOut:
    return EvalResultOut(
        test_case_id=orm.test_case_id,
        passed=orm.passed,
        score=orm.score,
        actual_output=orm.actual_output,
        latency_ms=orm.latency_ms,
        tokens_used=orm.tokens_used,
        safety_violations=orm.safety_violations,
    )


def _run_orm_to_out(orm: EvalRunORM, results: list[EvalResultORM]) -> EvalRunOut:
    return EvalRunOut(
        id=orm.id,
        suite_id=orm.suite_id,
        agent_version=orm.agent_version,
        status=orm.status.value,
        summary=orm.summary,
        started_at=orm.started_at,
        completed_at=orm.completed_at,
        results=[_result_orm_to_out(r) for r in results],
    )


@router.post(
    "/eval-suites", response_model=DataResponse[EvalSuite], status_code=status.HTTP_201_CREATED
)
async def create_eval_suite(
    payload: EvalSuiteCreate,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[EvalSuite]:
    suite = await crud_evals.create_eval_suite(session, payload)
    return DataResponse(data=suite)


@router.get("/eval-suites", response_model=ListResponse[EvalSuite])
async def list_eval_suites(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> ListResponse[EvalSuite]:
    suites, next_cursor = await crud_evals.list_eval_suites(session, limit, cursor)
    return ListResponse(data=suites, meta=ListMeta(next_cursor=next_cursor, limit=limit))


@router.get("/eval-suites/{suite_id}", response_model=DataResponse[EvalSuite])
async def get_eval_suite(
    suite_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[EvalSuite]:
    suite = await crud_evals.get_eval_suite(session, suite_id)
    return DataResponse(data=suite)


@router.post("/eval-suites/{suite_id}/run", response_model=DataResponse[EvalRunOut])
async def run_eval_suite(
    suite_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[EvalRunOut]:
    """Run every test case in the suite against its agent, score each, and persist results."""
    suite_orm = await crud_evals.get_eval_suite_orm(session, suite_id)
    agent = await crud_agents.get_agent(session, suite_orm.agent_id)

    llm_api_key = auth.encrypted_key or os.getenv("OPENAI_API_KEY", "")
    if not llm_api_key:
        raise EvalServiceError(
            "No LLM API key configured — set OPENAI_API_KEY or register a BYOK key"
        )

    eval_run_orm = await crud_eval_runs.create_eval_run(
        session, suite_id=suite_id, agent_version=1
    )
    await session.flush()

    eval_payload = {
        "agent": {
            "system_prompt": agent.system_prompt,
            "model": agent.model,
            "tool_names": [t.name for t in agent.tools],
            "api_key": llm_api_key,
            "max_tokens": agent.config.max_tokens,
            "temperature": agent.config.temperature,
            "timeout": agent.config.timeout,
            "max_iterations": 10,
            "safety_rules": agent.safety_policy.rules,
            "on_violation": agent.safety_policy.on_violation.value,
        },
        "test_cases": suite_orm.test_cases,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(300)) as client:
        try:
            resp = await client.post(f"{EVAL_SERVICE_URL}/api/v1/execute-suite", json=eval_payload)
            resp.raise_for_status()
            eval_result = resp.json()
        except httpx.HTTPError as e:
            raise EvalServiceError(f"Eval service call failed: {e}") from e

    eval_run_orm = await crud_eval_runs.complete_eval_run(
        session, eval_run_orm=eval_run_orm, results=eval_result.get("results", [])
    )
    results = await crud_eval_runs.get_eval_results(session, eval_run_orm.id)

    return DataResponse(data=_run_orm_to_out(eval_run_orm, results))


@router.get("/eval-runs/{eval_run_id}", response_model=DataResponse[EvalRunOut])
async def get_eval_run(
    eval_run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[EvalRunOut]:
    eval_run_orm = await crud_eval_runs.get_eval_run_orm(session, eval_run_id)
    results = await crud_eval_runs.get_eval_results(session, eval_run_id)
    return DataResponse(data=_run_orm_to_out(eval_run_orm, results))


@router.get(
    "/eval-runs/{eval_run_id}/compare/{other_run_id}", response_model=DataResponse[EvalCompareOut]
)
async def compare_eval_runs(
    eval_run_id: uuid.UUID,
    other_run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[EvalCompareOut]:
    """Compare two eval runs' summaries side by side (e.g. agent v1 vs v2)."""
    run_a_orm = await crud_eval_runs.get_eval_run_orm(session, eval_run_id)
    run_b_orm = await crud_eval_runs.get_eval_run_orm(session, other_run_id)
    results_a = await crud_eval_runs.get_eval_results(session, eval_run_id)
    results_b = await crud_eval_runs.get_eval_results(session, other_run_id)

    run_a = _run_orm_to_out(run_a_orm, results_a)
    run_b = _run_orm_to_out(run_b_orm, results_b)

    pass_rate_delta = None
    avg_latency_delta = None
    cost_delta = None
    if run_a.summary and run_b.summary:
        pass_rate_delta = run_b.summary.get("pass_rate", 0) - run_a.summary.get("pass_rate", 0)
        avg_latency_delta = run_b.summary.get("avg_latency_ms", 0) - run_a.summary.get(
            "avg_latency_ms", 0
        )
        cost_delta = run_b.summary.get("total_cost_usd", 0) - run_a.summary.get(
            "total_cost_usd", 0
        )

    return DataResponse(
        data=EvalCompareOut(
            run_a=run_a,
            run_b=run_b,
            pass_rate_delta=pass_rate_delta,
            avg_latency_ms_delta=avg_latency_delta,
            total_cost_usd_delta=cost_delta,
        )
    )
