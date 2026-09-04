"""Internal run endpoint — called by the API Gateway, not by end users directly."""

from dataclasses import asdict

from engine import execute_agent
from fastapi import APIRouter
from schemas import ExecuteRequest, ExecuteResponse, StepOut

router = APIRouter(prefix="/api/v1", tags=["execution"])


@router.post("/run", response_model=ExecuteResponse)
async def run_agent(req: ExecuteRequest) -> ExecuteResponse:
    """Execute the agent think->act->observe loop and return the full result."""
    result = await execute_agent(
        system_prompt=req.system_prompt,
        user_input=req.user_input,
        model=req.model,
        tool_names=req.tool_names,
        api_key=req.api_key,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        timeout=req.timeout,
        max_iterations=req.max_iterations,
        safety_rules=req.safety_rules,
        on_violation=req.on_violation,
        optimization=req.optimization,
        scope_mode=req.scope_mode,
        allowed_scope=req.allowed_scope,
    )
    return ExecuteResponse(
        output=result.output,
        steps=[StepOut(**asdict(s)) for s in result.steps],
        total_tokens_in=result.total_tokens_in,
        total_tokens_out=result.total_tokens_out,
        total_cost_usd=result.total_cost_usd,
        model=result.model,
        error=result.error,
        trace_id=result.trace_id,
    )
