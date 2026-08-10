"""Shared enums for agent/run/eval status fields (Pydantic models and ORM columns)."""

from enum import StrEnum


class AgentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunStepType(StrEnum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    SAFETY_CHECK = "safety_check"


class EvalRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SafetyViolationAction(StrEnum):
    BLOCK = "block"
    WARN = "warn"
    LOG = "log"
