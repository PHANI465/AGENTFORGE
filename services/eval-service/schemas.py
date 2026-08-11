"""Request/response schemas for the eval-service internal API."""

from typing import Any

from pydantic import BaseModel, Field


class AgentConfigIn(BaseModel):
    """The agent config needed to execute each test case, forwarded by the API Gateway."""

    system_prompt: str
    model: str
    tool_names: list[str] = Field(default_factory=list)
    api_key: str
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout: int = 120
    max_iterations: int = 10
    safety_rules: list[str] = Field(default_factory=list)
    on_violation: str = "log"


class TestCaseIn(BaseModel):
    id: str
    input: str
    expected_output: str | None = None
    expected_tool_calls: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ExecuteSuiteRequest(BaseModel):
    """Sent by the API Gateway to run an eval suite against an agent."""

    agent: AgentConfigIn
    test_cases: list[TestCaseIn]


class TestResultOut(BaseModel):
    test_case_id: str
    passed: bool
    score: float | None = None
    actual_output: str | None = None
    latency_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    safety_violations: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ExecuteSuiteResponse(BaseModel):
    results: list[TestResultOut] = Field(default_factory=list)
