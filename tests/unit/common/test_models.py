"""Unit tests for the shared Pydantic models in agentforge_common.models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from agentforge_common.enums import AgentStatus, SafetyViolationAction
from agentforge_common.models import (
    Agent,
    AgentConfig,
    AgentCreate,
    CostRecord,
    EvalResult,
    EvalSuite,
    EvalSuiteCreate,
    EvalTestCase,
    Run,
    RunCreate,
    RunStep,
    SafetyPolicy,
    TokenOptimizationConfig,
    ToolSpec,
)
from pydantic import ValidationError


def test_agent_config_defaults():
    config = AgentConfig()
    assert config.max_tokens == 1024
    assert config.temperature == 0.7
    assert config.timeout == 30
    assert config.retry_policy is None


def test_safety_policy_defaults_to_log():
    policy = SafetyPolicy()
    assert policy.rules == []
    assert policy.on_violation == SafetyViolationAction.LOG


def test_safety_policy_rejects_invalid_violation_action():
    with pytest.raises(ValidationError):
        SafetyPolicy(rules=["no PII"], on_violation="explode")


def test_tool_spec_requires_name_and_description():
    with pytest.raises(ValidationError):
        ToolSpec(description="missing name")


def test_agent_create_minimal():
    agent = AgentCreate(
        name="support-agent",
        model="gpt-4o-mini",
        system_prompt="Be helpful.",
    )
    assert agent.tools == []
    assert isinstance(agent.safety_policy, SafetyPolicy)
    assert isinstance(agent.config, AgentConfig)


def test_agent_full_round_trip():
    now = datetime.now(UTC)
    agent = Agent(
        id=uuid4(),
        name="support-agent",
        model="gpt-4o-mini",
        system_prompt="Be helpful.",
        tools=[
            ToolSpec(
                name="get_weather",
                description="Get current weather",
                parameters_schema={"type": "object", "properties": {"city": {"type": "string"}}},
            )
        ],
        safety_policy=SafetyPolicy(rules=["never share PII"], on_violation="block"),
        config=AgentConfig(max_tokens=2048),
        status=AgentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    dumped = agent.model_dump()
    assert dumped["status"] == "active"
    assert dumped["tools"][0]["name"] == "get_weather"

    restored = Agent.model_validate(dumped)
    assert restored == agent


def test_run_and_run_step_validate():
    run_id = uuid4()
    run = Run(
        id=run_id,
        agent_id=uuid4(),
        agent_version=1,
        input="hello",
        status="pending",
    )
    assert run.output is None
    assert run.started_at is None

    step = RunStep(
        id=uuid4(),
        run_id=run_id,
        step_number=1,
        type="llm_call",
        input={"messages": []},
        output={"content": "hi"},
        created_at=datetime.now(UTC),
    )
    assert step.type == "llm_call"


def test_eval_suite_and_result():
    agent_id = uuid4()
    suite = EvalSuite(
        id=uuid4(),
        name="smoke-suite",
        agent_id=agent_id,
        test_cases=[EvalTestCase(id="tc-1", input="hi", tags=["smoke"])],
        created_at=datetime.now(UTC),
    )
    assert suite.test_cases[0].expected_tool_calls == []

    result = EvalResult(
        id=uuid4(),
        eval_run_id=uuid4(),
        test_case_id="tc-1",
        passed=True,
        score=1.0,
        created_at=datetime.now(UTC),
    )
    assert result.safety_violations == []


def test_cost_record_requires_positive_token_fields_are_ints():
    record = CostRecord(
        id=uuid4(),
        agent_id=uuid4(),
        run_id=None,
        model="gpt-4o-mini",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.000123,
        created_at=datetime.now(UTC),
    )
    assert record.run_id is None
    assert record.tokens_in == 100


# ── Input validation hardening ──────────────────────────────────────


class TestAgentConfigBounds:
    def test_max_tokens_too_high(self):
        with pytest.raises(ValidationError):
            AgentConfig(max_tokens=200_000)

    def test_max_tokens_zero(self):
        with pytest.raises(ValidationError):
            AgentConfig(max_tokens=0)

    def test_temperature_negative(self):
        with pytest.raises(ValidationError):
            AgentConfig(temperature=-0.1)

    def test_temperature_above_2(self):
        with pytest.raises(ValidationError):
            AgentConfig(temperature=2.5)

    def test_timeout_too_high(self):
        with pytest.raises(ValidationError):
            AgentConfig(timeout=9999)

    def test_valid_boundary_values(self):
        cfg = AgentConfig(max_tokens=128_000, temperature=2.0, timeout=600)
        assert cfg.max_tokens == 128_000


class TestAgentNameLength:
    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            AgentCreate(name="", model="gpt-4o", system_prompt="hello")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            AgentCreate(name="x" * 201, model="gpt-4o", system_prompt="hello")


class TestRunCreateValidation:
    def test_empty_input_rejected(self):
        with pytest.raises(ValidationError):
            RunCreate(input="")

    def test_valid_input(self):
        rc = RunCreate(input="hello")
        assert rc.input == "hello"


class TestTokenOptimizationBounds:
    def test_negative_budget_rejected(self):
        with pytest.raises(ValidationError):
            TokenOptimizationConfig(daily_budget_usd=-1.0)

    def test_compression_threshold_too_low(self):
        with pytest.raises(ValidationError):
            TokenOptimizationConfig(compression_threshold_chars=50)


class TestEvalSuiteCreateValidation:
    def test_empty_suite_name_rejected(self):
        with pytest.raises(ValidationError):
            EvalSuiteCreate(name="", agent_id=uuid4())
