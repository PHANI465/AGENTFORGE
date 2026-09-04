"""Add knowledge_chunks table for per-agent RAG.

Each row is one embedded chunk of an agent's knowledge base. The embedding is
stored as a JSONB float array (no pgvector extension needed) — similarity is
computed in Python at retrieval time, which is fine at knowledge-base scale.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_knowledge_chunks_agent_id", "knowledge_chunks", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_agent_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
