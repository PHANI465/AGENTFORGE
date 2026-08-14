"""Shared Pydantic domain models used across the SDK, API Gateway, Agent Runtime,
and Eval Service.

Mirrors the data model in ARCHITECTURE.md. These are transport/validation models —
the SQLAlchemy ORM equivalents live in `agentforge_common.orm`.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from agentforge_common.enums import (
    AgentStatus,
    EvalRunStatus,
    RunStatus,
    RunStepType,
    SafetyViolationAction,
)


class SafetyPolicy(BaseModel):
    rules: list[str] = Field(default_factory=list)
    on_violation: SafetyViolationAction = SafetyViolationAction.LOG


class TokenOptimizationConfig(BaseModel):
    """Per-agent knobs for LLM cost/latency optimization (Milestone 7)."""

    enable_caching: bool = True
    enable_smart_routing: bool = False
    simple_model: str | None = Field(default=None, max_length=100)
    complex_model: str | None = Field(default=None, max_length=100)
    complexity_threshold: int = Field(default=200, ge=1, le=100_000)
    enable_compression: bool = False
    compression_threshold_chars: int = Field(default=2000, ge=100, le=1_000_000)
    daily_budget_usd: float | None = Field(default=None, ge=0.0, le=10_000.0)


class AgentConfig(BaseModel):
    max_tokens: int = Field(default=1024, ge=1, le=128_000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout: int = Field(default=30, ge=1, le=600)
    retry_policy: dict[str, Any] | None = None
    optimization: TokenOptimizationConfig = Field(default_factory=TokenOptimizationConfig)


class ToolSpec(BaseModel):
    """Wire-format description of a tool (no callable — that lives client-side in the SDK)."""

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    parameters_schema: dict[str, Any] = Field(default_factory=dict)


class AgentBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=100)
    system_prompt: str = Field(min_length=1, max_length=100_000)
    tools: list[ToolSpec] = Field(default_factory=list, max_length=50)
    safety_policy: SafetyPolicy = Field(default_factory=SafetyPolicy)
    config: AgentConfig = Field(default_factory=AgentConfig)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    tools: list[ToolSpec] | None = None
    safety_policy: SafetyPolicy | None = None
    config: AgentConfig | None = None
    status: AgentStatus | None = None


class Agent(AgentBase):
    id: UUID
    status: AgentStatus = AgentStatus.DRAFT
    created_at: datetime
    updated_at: datetime


class AgentVersion(BaseModel):
    id: UUID
    agent_id: UUID
    version: int
    snapshot: dict[str, Any]
    created_at: datetime


class ApiKey(BaseModel):
    """Read model — never includes the encrypted key or hash."""

    id: UUID
    user_id: str
    provider: str
    created_at: datetime


class Run(BaseModel):
    id: UUID
    agent_id: UUID
    agent_version: int
    input: str
    output: str | None = None
    status: RunStatus = RunStatus.PENDING
    trace_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RunStep(BaseModel):
    id: UUID
    run_id: UUID
    step_number: int
    type: RunStepType
    input: dict[str, Any]
    output: dict[str, Any]
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    created_at: datetime


class EvalTestCase(BaseModel):
    """Named to avoid colliding with pytest's TestCase collection heuristics."""

    id: str | None = None
    input: str
    expected_output: str | None = None
    expected_tool_calls: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class EvalSuite(BaseModel):
    id: UUID
    name: str
    agent_id: UUID
    test_cases: list[EvalTestCase] = Field(default_factory=list)
    created_at: datetime


class EvalSuiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    agent_id: UUID
    test_cases: list[EvalTestCase] = Field(default_factory=list, max_length=500)


class EvalRun(BaseModel):
    id: UUID
    suite_id: UUID
    agent_version: int
    status: EvalRunStatus = EvalRunStatus.PENDING
    summary: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EvalResult(BaseModel):
    id: UUID
    eval_run_id: UUID
    test_case_id: str
    passed: bool
    score: float | None = None
    actual_output: str | None = None
    latency_ms: int | None = None
    tokens_used: int | None = None
    safety_violations: list[str] = Field(default_factory=list)
    created_at: datetime


class RunCreate(BaseModel):
    """Input payload for POST /api/v1/agents/{id}/run."""

    input: str = Field(min_length=1, max_length=100_000)


class CostRecord(BaseModel):
    id: UUID
    agent_id: UUID
    run_id: UUID | None = None
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: datetime
