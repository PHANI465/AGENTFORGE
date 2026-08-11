"""Request/response schemas for the agent-runtime internal API."""

from typing import Any

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    """Sent by the API Gateway to trigger an agent run."""

    system_prompt: str
    user_input: str
    model: str
    tool_names: list[str] = Field(default_factory=list)
    api_key: str
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout: int = 120
    max_iterations: int = 10
    safety_rules: list[str] = Field(default_factory=list)
    on_violation: str = "log"


class StepOut(BaseModel):
    step_number: int
    type: str
    input: dict[str, Any]
    output: dict[str, Any]
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0


class ExecuteResponse(BaseModel):
    output: str
    steps: list[StepOut] = Field(default_factory=list)
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    model: str = ""
    error: str | None = None
    trace_id: str | None = None
