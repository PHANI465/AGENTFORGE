"""Add multi-tenant users table and owner_id scoping columns.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-18

Adds a `users` table and a NOT NULL `owner_id` FK to `agents`, `runs`,
`eval_suites`, `cost_records`, and `api_keys` — the tables every
list/get/update/delete query in services/api-gateway reads or writes with
zero caller scoping today (see docs/security.md's tenancy section).
`api_keys` keeps its existing free-text `user_id` label alongside the new
FK; "claiming" a pre-tenancy key later means updating its `owner_id` away
from the system user below, not going from NULL to a real value — keeping
every owner_id column uniformly NOT NULL avoids a NULL-vs-system-user
equivalence that queries would otherwise have to special-case.

Existing rows are backfilled onto a well-known system/demo user before the
NOT NULL constraint is added, so this migration is safe to run against a
database that already has agents/runs/etc. in it (e.g. anything seeded by
scripts/seed.py).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from agentforge_common.orm import SYSTEM_USER_ID
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OWNED_TABLES = ("agents", "runs", "eval_suites", "cost_records", "api_keys")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("oauth_provider", sa.String(), nullable=True),
        sa.Column("oauth_subject", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    users_table = sa.table(
        "users",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("email", sa.String()),
        sa.column("name", sa.String()),
    )
    op.bulk_insert(
        users_table,
        [
            {
                "id": SYSTEM_USER_ID,
                "email": "system@agentforge.local",
                "name": "System (pre-tenancy data)",
            }
        ],
    )

    for table_name in _OWNED_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "owner_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )
        # A fresh column object per iteration — sa.table() binds a column to
        # its parent table on construction (sets column.table), so reusing
        # one column instance across multiple tables raises "already
        # assigned to table" on the second iteration.
        owner_id_col = sa.column("owner_id", postgresql.UUID(as_uuid=True))
        table = sa.table(table_name, owner_id_col)
        op.execute(
            table.update().where(owner_id_col.is_(None)).values(owner_id=SYSTEM_USER_ID)
        )
        op.alter_column(table_name, "owner_id", nullable=False)
        op.create_index(f"ix_{table_name}_owner_id", table_name, ["owner_id"])


def downgrade() -> None:
    for table_name in reversed(_OWNED_TABLES):
        op.drop_index(f"ix_{table_name}_owner_id", table_name=table_name)
        op.drop_column(table_name, "owner_id")

    op.drop_table("users")
