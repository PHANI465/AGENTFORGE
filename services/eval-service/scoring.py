"""Scoring functions for eval test case results: LLM-as-judge accuracy, tool-call correctness."""

import json

import litellm

JUDGE_SYSTEM_PROMPT = (
    "You are grading an AI agent's response. Given the user's input, the agent's "
    "actual output, and the expected output, decide whether the actual output "
    "satisfies the expected output's intent. Respond with strict JSON only: "
    '{"score": <float 0.0-1.0>, "reasoning": "<one sentence>"}.'
)


def tool_correctness(actual_tool_names: list[str], expected_tool_calls: list[str]) -> float | None:
    """Fraction of expected tools that were actually called. None if no expectation was set."""
    if not expected_tool_calls:
        return None
    expected = set(expected_tool_calls)
    actual = set(actual_tool_names)
    return len(expected & actual) / len(expected)


async def judge_accuracy(
    user_input: str,
    actual_output: str,
    expected_output: str | None,
    model: str,
    api_key: str,
) -> float | None:
    """Score how well actual_output satisfies expected_output, using the agent's own
    model as an LLM judge. Returns None if there's no expected_output to grade against."""
    if not expected_output:
        return None

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User input: {user_input}\n\n"
                f"Expected output: {expected_output}\n\n"
                f"Actual output: {actual_output}"
            ),
        },
    ]

    try:
        response = await litellm.acompletion(
            model=model, messages=messages, api_key=api_key,
            max_tokens=200, temperature=0.0,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        score = float(parsed.get("score", 0.0))
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.0


def combine_score(
    accuracy: float | None, tool_score: float | None, safety_violation_count: int
) -> tuple[float, bool]:
    """Combine sub-scores into one overall score and pass/fail verdict.

    A test case with no expected_output and no expected_tool_calls has nothing to
    grade, so it defaults to passing (score 1.0) unless a safety rule was violated.
    """
    scores = [s for s in (accuracy, tool_score) if s is not None]
    combined = sum(scores) / len(scores) if scores else 1.0
    passed = combined >= 0.7 and safety_violation_count == 0
    return combined, passed
