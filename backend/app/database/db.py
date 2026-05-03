"""
SQLAlchemy ORM models — one table per concern.
All tables live in one database so pgvector embeddings and user data are co-located.
"""

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class User(Base):
    """Registered user. Every agent run is scoped to a user."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Where the finished trip plan is emailed — defaults to registration email
    webhook_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="user")


class AgentRun(Base):
    """One row per user query. Stores the full query → response lifecycle."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Which tools fired, in order — stored as a JSON list of tool names
    tools_used: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Token usage split by model so we can report cost per query
    haiku_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sonnet_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="runs")
    tool_calls: Mapped[list["ToolCallLog"]] = relationship(
        "ToolCallLog", back_populates="run"
    )


class ToolCallLog(Base):
    """One row per tool invocation inside an agent run. Used for the trace panel in the UI."""

    __tablename__ = "tool_call_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Wall-clock ms so we can spot slow tools
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tool_calls")


class DocumentChunk(Base):
    """
    RAG knowledge base. Each row is a chunk of destination text
    plus its 384-dim embedding from all-MiniLM-L6-v2.
    pgvector does cosine similarity search directly in SQL.
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    destination: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    travel_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # "overview" or "practical_guide" — lets us filter by doc type if needed
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, default="overview")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # 384 dims matches all-MiniLM-L6-v2 output exactly
    embedding: Mapped[list] = mapped_column(Vector(384), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
