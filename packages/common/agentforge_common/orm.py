"""SQLAlchemy ORM models — the Postgres schema from ARCHITECTURE.md's Data Model section."""

import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from agentforge_common.db import Base
from agentforge_common.enums import AgentStatus, EvalRunStatus, RunStatus, RunStepType


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _str_enum(enum_cls: type, name: str) -> SAEnum:
    """SAEnum bound by member *value* (e.g. "active"), not member *name* (e.g. "ACTIVE") —
    SQLAlchemy's default binds by name, which doesn't match the lowercase Postgres enum values."""
    return SAEnum(enum_cls, name=name, values_callable=lambda cls: [e.value for e in cls])


# Fixed id of the system/demo user that pre-tenancy data (and any API key
# never explicitly claimed by a real account) is scoped to. Must match
# alembic/versions/0003_add_tenancy.py's SYSTEM_USER_ID exactly.
SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(default=None)
    oauth_provider: Mapped[str | None] = mapped_column(default=None)
    oauth_subject: Mapped[str | None] = mapped_column(default=None)
    name: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AgentORM(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str]
    model: Mapped[str]
    system_prompt: Mapped[str] = mapped_column(Text)
    tools_config: Mapped[list] = mapped_column(JSONB, default=list)
    safety_policy: Mapped[dict] = mapped_column(JSONB, default=dict)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[AgentStatus] = mapped_column(
        _str_enum(AgentStatus, "agent_status"), default=AgentStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    versions: Mapped[list["AgentVersionORM"]] = relationship(
        back_populates="agent", passive_deletes=True
    )


class AgentVersionORM(Base):
    __tablename__ = "agent_versions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    version: Mapped[int]
    snapshot: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    agent: Mapped["AgentORM"] = relationship(back_populates="versions")


class KnowledgeChunkORM(Base):
    """One embedded chunk of an agent's knowledge base (RAG). Stored per agent;
    the embedding is a plain JSON float array so we need no pgvector extension —
    similarity is computed in Python, which is fine at demo/knowledge-base scale.
    """

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(default="")
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ApiKeyORM(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = _uuid_pk()
    key_hash: Mapped[str] = mapped_column(unique=True, index=True)
    user_id: Mapped[str] = mapped_column(index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str]
    encrypted_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RunORM(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    agent_version: Mapped[int]
    input: Mapped[str] = mapped_column(Text)
    output: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[RunStatus] = mapped_column(
        _str_enum(RunStatus, "run_status"), default=RunStatus.PENDING
    )
    trace_id: Mapped[str | None] = mapped_column(default=None, index=True)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    steps: Mapped[list["RunStepORM"]] = relationship(back_populates="run")


class RunStepORM(Base):
    __tablename__ = "run_steps"

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    step_number: Mapped[int]
    type: Mapped[RunStepType] = mapped_column(_str_enum(RunStepType, "run_step_type"))
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict] = mapped_column(JSONB, default=dict)
    tokens_in: Mapped[int | None] = mapped_column(default=None)
    tokens_out: Mapped[int | None] = mapped_column(default=None)
    latency_ms: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    run: Mapped["RunORM"] = relationship(back_populates="steps")


class EvalSuiteORM(Base):
    __tablename__ = "eval_suites"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str]
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    test_cases: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    eval_runs: Mapped[list["EvalRunORM"]] = relationship(back_populates="suite")


class EvalRunORM(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    suite_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_suites.id", ondelete="CASCADE"))
    agent_version: Mapped[int]
    status: Mapped[EvalRunStatus] = mapped_column(
        _str_enum(EvalRunStatus, "eval_run_status"), default=EvalRunStatus.PENDING
    )
    summary: Mapped[dict | None] = mapped_column(JSONB, default=None)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    suite: Mapped["EvalSuiteORM"] = relationship(back_populates="eval_runs")
    results: Mapped[list["EvalResultORM"]] = relationship(back_populates="eval_run")


class EvalResultORM(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = _uuid_pk()
    eval_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE")
    )
    test_case_id: Mapped[str]
    passed: Mapped[bool]
    score: Mapped[float | None] = mapped_column(default=None)
    actual_output: Mapped[str | None] = mapped_column(Text, default=None)
    latency_ms: Mapped[int | None] = mapped_column(default=None)
    tokens_used: Mapped[int | None] = mapped_column(default=None)
    safety_violations: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    eval_run: Mapped["EvalRunORM"] = relationship(back_populates="results")


class CostRecordORM(Base):
    __tablename__ = "cost_records"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), default=None
    )
    model: Mapped[str]
    tokens_in: Mapped[int]
    tokens_out: Mapped[int]
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
