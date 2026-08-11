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
from agentforge_common.envelope import DataResponse
from agentforge_common.exceptions import AgentForgeError
from agentforge_common.models import Run, RunCreate
from agentforge_common.orm import ApiKeyORM
from dependencies import get_db, require_api_key
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/agents", tags=["runs"])

AGENT_RUNTIME_URL = os.getenv("AGENT_RUNTIME_URL", "http://localhost:8001")


class RuntimeError_(AgentForgeError):
    code = "runtime_error"


@router.post("/{agent_id}/run", response_model=DataResponse[Run])
async def run_agent(
    agent_id: uuid.UUID,
    payload: RunCreate,
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Run]:
    """Execute an agent: look up config, call runtime, persist results."""
    agent = await crud_agents.get_agent(session, agent_id)

    tool_names = [t.name for t in agent.tools]

    llm_api_key = auth.encrypted_key or os.getenv("OPENAI_API_KEY", "")
    if not llm_api_key:
        raise RuntimeError_("No LLM API key configured — set OPENAI_API_KEY or register a BYOK key")

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
    )

    return DataResponse(data=run)
