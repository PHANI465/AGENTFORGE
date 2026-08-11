"""Unit tests for eval-service scoring: tool correctness and score combination.

judge_accuracy (which calls an LLM) is exercised only via the mocked integration
tests — these tests cover the deterministic, non-LLM scoring logic.
"""

import sys
from pathlib import Path

EVAL_SERVICE_DIR = Path(__file__).resolve().parents[3] / "services" / "eval-service"
if str(EVAL_SERVICE_DIR) not in sys.path:
    sys.path.append(str(EVAL_SERVICE_DIR))

from scoring import combine_score, tool_correctness  # noqa: E402


class TestToolCorrectness:
    def test_no_expectation_returns_none(self):
        assert tool_correctness(["get_weather"], []) is None

    def test_all_expected_tools_called(self):
        assert tool_correctness(["get_weather", "calculate"], ["get_weather"]) == 1.0

    def test_none_of_expected_tools_called(self):
        assert tool_correctness(["calculate"], ["get_weather"]) == 0.0

    def test_partial_match(self):
        score = tool_correctness(["get_weather"], ["get_weather", "search_web"])
        assert score == 0.5

    def test_extra_actual_tools_dont_hurt_score(self):
        score = tool_correctness(
            ["get_weather", "calculate", "search_web"], ["get_weather"]
        )
        assert score == 1.0


class TestCombineScore:
    def test_no_subscores_defaults_to_pass(self):
        combined, passed = combine_score(None, None, 0)
        assert combined == 1.0
        assert passed is True

    def test_no_subscores_but_safety_violation_fails(self):
        combined, passed = combine_score(None, None, 1)
        assert combined == 1.0
        assert passed is False

    def test_accuracy_only(self):
        combined, passed = combine_score(0.9, None, 0)
        assert combined == 0.9
        assert passed is True

    def test_low_accuracy_fails(self):
        combined, passed = combine_score(0.3, None, 0)
        assert combined == 0.3
        assert passed is False

    def test_accuracy_and_tool_score_averaged(self):
        combined, passed = combine_score(1.0, 0.5, 0)
        assert combined == 0.75
        assert passed is True

    def test_threshold_boundary_passes(self):
        combined, passed = combine_score(0.7, None, 0)
        assert combined == 0.7
        assert passed is True

    def test_safety_violation_overrides_high_score(self):
        combined, passed = combine_score(1.0, 1.0, 2)
        assert combined == 1.0
        assert passed is False
