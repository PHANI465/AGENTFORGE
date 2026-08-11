"""Test case runner: executes eval test cases against agent-runtime and scores each result."""

import os
import time

import httpx
from schemas import AgentConfigIn, TestCaseIn, TestResultOut
from scoring import combine_score, judge_accuracy, tool_correctness

AGENT_RUNTIME_URL = os.getenv("AGENT_RUNTIME_URL", "http://localhost:8001")


async def run_test_case(agent: AgentConfigIn, test_case: TestCaseIn) -> TestResultOut:
    """Execute one test case's input against the agent via agent-runtime, then score the result."""
    payload = {
        "system_prompt": agent.system_prompt,
        "user_input": test_case.input,
        "model": agent.model,
        "tool_names": agent.tool_names,
        "api_key": agent.api_key,
        "max_tokens": agent.max_tokens,
        "temperature": agent.temperature,
        "timeout": agent.timeout,
        "max_iterations": agent.max_iterations,
        "safety_rules": agent.safety_rules,
        "on_violation": agent.on_violation,
    }

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(agent.timeout + 10)) as client:
            resp = await client.post(f"{AGENT_RUNTIME_URL}/api/v1/run", json=payload)
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPError as e:
        return TestResultOut(
            test_case_id=test_case.id, passed=False, score=0.0,
            error=f"Agent runtime call failed: {e}",
        )
    latency_ms = int((time.monotonic() - start) * 1000)

    actual_output = result.get("output", "")
    steps = result.get("steps", [])
    actual_tool_names = [
        s["input"].get("tool_name")
        for s in steps
        if s.get("type") == "tool_call" and s.get("input", {}).get("tool_name")
    ]
    safety_violations = [
        v
        for s in steps if s.get("type") == "safety_check"
        for v in s.get("output", {}).get("violations", [])
    ]

    tool_score = tool_correctness(actual_tool_names, test_case.expected_tool_calls)
    accuracy_score = await judge_accuracy(
        user_input=test_case.input, actual_output=actual_output,
        expected_output=test_case.expected_output,
        model=agent.model, api_key=agent.api_key,
    )

    combined, passed = combine_score(accuracy_score, tool_score, len(safety_violations))

    return TestResultOut(
        test_case_id=test_case.id,
        passed=passed and not result.get("error"),
        score=combined,
        actual_output=actual_output,
        latency_ms=latency_ms,
        tokens_used=result.get("total_tokens_in", 0) + result.get("total_tokens_out", 0),
        cost_usd=result.get("total_cost_usd", 0.0),
        safety_violations=safety_violations,
        error=result.get("error"),
    )
