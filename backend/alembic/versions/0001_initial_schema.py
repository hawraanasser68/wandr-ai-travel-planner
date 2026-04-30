"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-29
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension — must exist before Vector columns are created
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("webhook_email", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── agent_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=True),
        sa.Column("tools_used", JSON, nullable=True),
        sa.Column("haiku_tokens", sa.Integer, nullable=True),
        sa.Column("sonnet_tokens", sa.Integer, nullable=True),
        sa.Column("cost_usd", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])

    # ── tool_call_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "tool_call_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input_data", JSON, nullable=True),
        sa.Column("output_data", JSON, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_tool_call_logs_run_id", "tool_call_logs", ["run_id"])

    # ── document_chunks ────────────────────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("destination", sa.String(255), nullable=False),
        sa.Column("travel_style", sa.String(50), nullable=True),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source", sa.String(500), nullable=True),
        # Vector(384) — pgvector column for cosine similarity search
        sa.Column("embedding", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_document_chunks_destination", "document_chunks", ["destination"])

    # Change embedding column type to vector(384) using raw SQL
    # (SQLAlchemy doesn't natively know the vector type without pgvector registered)
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384)")


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("tool_call_logs")
    op.drop_table("agent_runs")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
