"""Safety policy enforcement — checks content against rules before it leaves the agent.

Two check points in the execution loop:
  1. Post-LLM response: scan the model's text output for violations.
  2. Pre-tool call: scan tool arguments for violations.

Enforcement modes (per-agent, set on the SafetyPolicy):
  - block: halt execution immediately, return a blocked message.
  - warn:  flag the violation in the step trace, but continue.
  - log:   record the violation silently, continue unchanged.
"""

import re
from dataclasses import dataclass, field
from enum import StrEnum

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email_address", _EMAIL_RE),
    ("phone_number", _PHONE_RE),
    ("ssn", _SSN_RE),
    ("credit_card", _CREDIT_CARD_RE),
]


class CheckPoint(StrEnum):
    POST_LLM = "post_llm"
    PRE_TOOL = "pre_tool"


@dataclass
class SafetyViolation:
    rule: str
    matched_text: str
    pattern_name: str
    check_point: str


@dataclass
class CheckResult:
    """Outcome of a safety check."""

    passed: bool
    violations: list[SafetyViolation] = field(default_factory=list)


class SafetyChecker:
    """Evaluates content against the agent's safety rules.

    Rule interpretation:
      - Any rule containing "pii" (case-insensitive): activates built-in PII
        pattern detection (email, phone, SSN, credit card).
      - Rules starting with "block_keywords:": comma-separated keywords that
        must not appear in content (case-insensitive).
      - All other rules: stored for future LLM-as-judge evaluation (not
        pattern-matched today).
    """

    def __init__(self, rules: list[str], on_violation: str = "log") -> None:
        self.rules = rules
        self.on_violation = on_violation
        self._pii_active = any("pii" in r.lower() for r in rules)
        self._blocked_keywords = self._extract_keywords(rules)
        self._pii_rules = [r for r in rules if "pii" in r.lower()]

    @staticmethod
    def _extract_keywords(rules: list[str]) -> list[str]:
        keywords: list[str] = []
        for rule in rules:
            if rule.lower().startswith("block_keywords:"):
                raw = rule.split(":", 1)[1]
                keywords.extend(k.strip().lower() for k in raw.split(",") if k.strip())
        return keywords

    def check(self, content: str, check_point: CheckPoint) -> CheckResult:
        """Run all applicable checks against content."""
        if not content:
            return CheckResult(passed=True)

        violations: list[SafetyViolation] = []

        if self._pii_active:
            violations.extend(self._check_pii(content, check_point))

        if self._blocked_keywords:
            violations.extend(self._check_keywords(content, check_point))

        return CheckResult(passed=len(violations) == 0, violations=violations)

    def _check_pii(self, content: str, check_point: CheckPoint) -> list[SafetyViolation]:
        violations: list[SafetyViolation] = []
        rule_text = self._pii_rules[0] if self._pii_rules else "no_pii"
        for pattern_name, regex in _PII_PATTERNS:
            for match in regex.finditer(content):
                violations.append(SafetyViolation(
                    rule=rule_text,
                    matched_text=match.group(),
                    pattern_name=pattern_name,
                    check_point=check_point.value,
                ))
        return violations

    def _check_keywords(self, content: str, check_point: CheckPoint) -> list[SafetyViolation]:
        violations: list[SafetyViolation] = []
        content_lower = content.lower()
        for keyword in self._blocked_keywords:
            if keyword in content_lower:
                violations.append(SafetyViolation(
                    rule=f"block_keywords:{keyword}",
                    matched_text=keyword,
                    pattern_name="blocked_keyword",
                    check_point=check_point.value,
                ))
        return violations

    @property
    def should_block(self) -> bool:
        return self.on_violation == "block"

    @property
    def should_warn(self) -> bool:
        return self.on_violation == "warn"

    @property
    def has_rules(self) -> bool:
        return len(self.rules) > 0
