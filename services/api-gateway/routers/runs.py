"""Run routes — POST /api/v1/agents/{id}/run.

Authenticates the request, loads the agent config, calls the agent-runtime
service, and persists the Run/RunStep/CostRecord results to Postgres.
"""

import os
import uuid

import crud_agents
import crud_runs
import httpx
from agentforge_common.enums import RunStatus
from agentforge_common.envelope import DataResponse, ListMeta, ListResponse
from agentforge_common.exceptions import AgentForgeError, BudgetExceededError
from agentforge_common.models import Run, RunCreate
from agentforge_common.orm import ApiKeyORM
from agentforge_common.security import decrypt_key
from dependencies import get_db, require_api_key
from fastapi import APIRouter, Depends, Query, Request
from rate_limit import RATE_LIMIT_DEFAULT, RATE_LIMIT_RUN, limiter
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/agents", tags=["runs"])

AGENT_RUNTIME_URL = os.getenv("AGENT_RUNTIME_URL", "http://localhost:8001")


class RuntimeError_(AgentForgeError):
    code = "runtime_error"


@router.post(
    "/{agent_id}/run",
    response_model=DataResponse[Run],
    summary="Execute an agent",
    operation_id="runAgent",
)
@limiter.limit(RATE_LIMIT_RUN)
async def run_agent(
    request: Request,
    agent_id: uuid.UUID,
    payload: RunCreate,
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Run]:
    """Execute an agent: look up config, call runtime, persist results."""
    agent = await crud_agents.get_agent(session, agent_id)

    tool_names = [t.name for t in agent.tools]

    llm_api_key = decrypt_key(auth.encrypted_key) or os.getenv("OPENAI_API_KEY", "")
    if not llm_api_key:
        raise RuntimeError_("No LLM API key configured — set OPENAI_API_KEY or register a BYOK key")

    daily_budget = agent.config.optimization.daily_budget_usd
    if daily_budget is not None:
        spent_today = await crud_runs.get_agent_spend_today(session, agent.id)
        if spent_today >= daily_budget:
            raise BudgetExceededError(
                f"Daily budget of ${daily_budget:.6f} exceeded "
                f"(spent ${spent_today:.6f} today)"
            )

    run_orm = await crud_runs.create_run(
        session, agent_id=agent.id, agent_version=1, user_input=payload.input,
    )
    run_orm.status = RunStatus.RUNNING
    await session.flush()

    runtime_payload = {
        "system_prompt": agent.system_prompt,
        "user_input": payload.input,
        "model": agent.model,
        "tool_names": tool_names,
        "api_key": llm_api_key,
        "max_tokens": agent.config.max_tokens,
        "temperature": agent.config.temperature,
        "timeout": agent.config.timeout,
        "max_iterations": 10,
        "safety_rules": agent.safety_policy.rules,
        "on_violation": agent.safety_policy.on_violation.value,
        "optimization": agent.config.optimization.model_dump(),
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(agent.config.timeout + 10)) as client:
        try:
            resp = await client.post(f"{AGENT_RUNTIME_URL}/api/v1/run", json=runtime_payload)
            resp.raise_for_status()
            result = resp.json()
        except httpx.HTTPStatusError as e:
            run_status = RunStatus.FAILED
            result = {"output": "", "steps": [], "total_tokens_in": 0,
                      "total_tokens_out": 0, "total_cost_usd": 0.0,
                      "model": agent.model,
                      "error": f"Runtime returned {e.response.status_code}"}
        except httpx.RequestError as e:
            run_status = RunStatus.FAILED
            result = {"output": "", "steps": [], "total_tokens_in": 0,
                      "total_tokens_out": 0, "total_cost_usd": 0.0,
                      "model": agent.model, "error": str(e)}

    run_status = RunStatus.FAILED if result.get("error") else RunStatus.COMPLETED

    run = await crud_runs.complete_run(
        session,
        run_orm=run_orm,
        output=result.get("output", ""),
        status=run_status,
        steps_data=result.get("steps", []),
        model=result.get("model", agent.model),
        total_tokens_in=result.get("total_tokens_in", 0),
        total_tokens_out=result.get("total_tokens_out", 0),
        total_cost_usd=result.get("total_cost_usd", 0.0),
        trace_id=result.get("trace_id"),
    )

    return DataResponse(data=run)


@router.get(
    "/{agent_id}/runs",
    response_model=ListResponse[Run],
    summary="List runs for an agent",
    operation_id="listAgentRuns",
)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def list_agent_runs(
    request: Request,
    agent_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> ListResponse[Run]:
    """Most recent runs for an agent, newest first."""
    runs = await crud_runs.list_runs_for_agent(session, agent_id, limit)
    total = await crud_runs.count_runs_for_agent(session, agent_id)
    return ListResponse(
        data=runs, meta=ListMeta(total=total, next_cursor=None, limit=limit),
    )
