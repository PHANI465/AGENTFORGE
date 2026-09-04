"""Add 'scope_check' to the run_step_type enum.

The topic/scope guard records a `scope_check` step when it classifies an
agent's input. The run_step_type Postgres enum (created in 0001) only knew
llm_call/tool_call/safety_check, so inserting a scope_check step would fail
with an invalid-enum-value error until this value is added.

Postgres 12+ allows ALTER TYPE ... ADD VALUE inside a transaction; the value
is only usable after commit, which is fine here since this migration only
adds it and nothing in the same transaction inserts a row using it.
"""

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE run_step_type ADD VALUE IF NOT EXISTS 'scope_check'")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE; removing an enum value means
    # recreating the type. Not worth it for an additive, backward-compatible
    # value — downgrade is intentionally a no-op.
    pass
