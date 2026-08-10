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
    EvalTestCase,
    Run,
    RunStep,
    SafetyPolicy,
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
