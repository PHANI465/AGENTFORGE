"""Add trace_id column to runs table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("trace_id", sa.String(), nullable=True))
    op.create_index("ix_runs_trace_id", "runs", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_runs_trace_id", table_name="runs")
    op.drop_column("runs", "trace_id")
