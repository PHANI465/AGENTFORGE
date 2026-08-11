"""Unit tests for the SafetyChecker — PII detection, keyword blocking, enforcement modes."""

import sys
from pathlib import Path

AGENT_RUNTIME_DIR = Path(__file__).resolve().parents[3] / "services" / "agent-runtime"
if str(AGENT_RUNTIME_DIR) not in sys.path:
    sys.path.append(str(AGENT_RUNTIME_DIR))

from safety import CheckPoint, SafetyChecker  # noqa: E402


class TestPIIDetection:
    def test_detects_email(self):
        checker = SafetyChecker(rules=["never share customer PII"], on_violation="block")
        result = checker.check("Contact john@example.com for details.", CheckPoint.POST_LLM)
        assert not result.passed
        assert len(result.violations) == 1
        assert result.violations[0].pattern_name == "email_address"
        assert result.violations[0].matched_text == "john@example.com"

    def test_detects_phone_number(self):
        checker = SafetyChecker(rules=["no pii allowed"], on_violation="block")
        result = checker.check("Call us at 555-123-4567.", CheckPoint.POST_LLM)
        assert not result.passed
        assert any(v.pattern_name == "phone_number" for v in result.violations)

    def test_detects_ssn(self):
        checker = SafetyChecker(rules=["pii"], on_violation="block")
        result = checker.check("SSN: 123-45-6789", CheckPoint.POST_LLM)
        assert not result.passed
        assert any(v.pattern_name == "ssn" for v in result.violations)

    def test_detects_credit_card(self):
        checker = SafetyChecker(rules=["no PII"], on_violation="block")
        result = checker.check("Card: 4111 1111 1111 1111", CheckPoint.POST_LLM)
        assert not result.passed
        assert any(v.pattern_name == "credit_card" for v in result.violations)

    def test_detects_multiple_pii_types(self):
        checker = SafetyChecker(rules=["pii"], on_violation="block")
        result = checker.check(
            "Email: a@b.com, Phone: 555-000-1234, SSN: 111-22-3333",
            CheckPoint.POST_LLM,
        )
        assert not result.passed
        pattern_names = {v.pattern_name for v in result.violations}
        assert "email_address" in pattern_names
        assert "phone_number" in pattern_names
        assert "ssn" in pattern_names

    def test_clean_content_passes(self):
        checker = SafetyChecker(rules=["no pii"], on_violation="block")
        result = checker.check("The weather today is sunny.", CheckPoint.POST_LLM)
        assert result.passed
        assert len(result.violations) == 0

    def test_pii_not_active_without_pii_rule(self):
        checker = SafetyChecker(rules=["be polite"], on_violation="block")
        result = checker.check("Contact john@example.com", CheckPoint.POST_LLM)
        assert result.passed


class TestKeywordBlocking:
    def test_blocks_keyword(self):
        checker = SafetyChecker(
            rules=["block_keywords:password,secret"], on_violation="block"
        )
        result = checker.check("Your password is abc123", CheckPoint.POST_LLM)
        assert not result.passed
        assert result.violations[0].pattern_name == "blocked_keyword"

    def test_keyword_case_insensitive(self):
        checker = SafetyChecker(
            rules=["block_keywords:secret"], on_violation="block"
        )
        result = checker.check("This is a SECRET document", CheckPoint.POST_LLM)
        assert not result.passed

    def test_keyword_clean_passes(self):
        checker = SafetyChecker(
            rules=["block_keywords:password,secret"], on_violation="block"
        )
        result = checker.check("The weather is nice.", CheckPoint.POST_LLM)
        assert result.passed

    def test_multiple_keyword_rules(self):
        checker = SafetyChecker(
            rules=["block_keywords:foo", "block_keywords:bar"], on_violation="block"
        )
        result = checker.check("This is a bar fight.", CheckPoint.POST_LLM)
        assert not result.passed


class TestCombinedRules:
    def test_pii_and_keywords_together(self):
        checker = SafetyChecker(
            rules=["no pii", "block_keywords:internal"], on_violation="block"
        )
        result = checker.check(
            "Internal doc: call 555-123-4567", CheckPoint.POST_LLM
        )
        assert not result.passed
        pattern_names = {v.pattern_name for v in result.violations}
        assert "phone_number" in pattern_names
        assert "blocked_keyword" in pattern_names


class TestEnforcementModes:
    def test_block_mode_properties(self):
        checker = SafetyChecker(rules=["pii"], on_violation="block")
        assert checker.should_block is True
        assert checker.should_warn is False

    def test_warn_mode_properties(self):
        checker = SafetyChecker(rules=["pii"], on_violation="warn")
        assert checker.should_block is False
        assert checker.should_warn is True

    def test_log_mode_properties(self):
        checker = SafetyChecker(rules=["pii"], on_violation="log")
        assert checker.should_block is False
        assert checker.should_warn is False


class TestCheckPoints:
    def test_pre_tool_check_point(self):
        checker = SafetyChecker(rules=["pii"], on_violation="block")
        result = checker.check("email: test@test.com", CheckPoint.PRE_TOOL)
        assert not result.passed
        assert result.violations[0].check_point == "pre_tool"

    def test_post_llm_check_point(self):
        checker = SafetyChecker(rules=["pii"], on_violation="block")
        result = checker.check("email: test@test.com", CheckPoint.POST_LLM)
        assert not result.passed
        assert result.violations[0].check_point == "post_llm"


class TestEdgeCases:
    def test_empty_content_passes(self):
        checker = SafetyChecker(rules=["pii"], on_violation="block")
        result = checker.check("", CheckPoint.POST_LLM)
        assert result.passed

    def test_no_rules_always_passes(self):
        checker = SafetyChecker(rules=[], on_violation="block")
        result = checker.check("Contact john@example.com", CheckPoint.POST_LLM)
        assert result.passed

    def test_has_rules_property(self):
        assert SafetyChecker(rules=[], on_violation="log").has_rules is False
        assert SafetyChecker(rules=["pii"], on_violation="log").has_rules is True
