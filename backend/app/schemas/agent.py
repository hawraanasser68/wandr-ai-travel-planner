"""
Agent schemas — the HTTP request/response shapes for the /agent endpoints.
Also defines the StreamChunk format used for Server-Sent Events (SSE).
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Incoming request ───────────────────────────────────────────────────────────

class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentQueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    # Previous messages in the conversation — enables multi-turn chat
    history: list[HistoryMessage] = []

    # Optional context hints — passed to the ML classifier for richer classification
    country: str = "Unknown"
    avg_cost_per_day: float = Field(default=100.0, ge=0, le=10000)
    family_friendly: bool = False


# ── SSE streaming chunk ────────────────────────────────────────────────────────
# Each chunk is a JSON line pushed over the SSE stream.
# The frontend reads `type` to decide how to render it.

class StreamChunk(BaseModel):
    type: Literal["token", "tool_call", "tool_result", "done", "error"]
    content: str = ""          # token text, tool name, error message, or "" for done
    run_id: uuid.UUID | None = None   # populated on the "done" event


# ── Non-streaming response (used by /agent/runs/{id} history endpoint) ─────────

class ToolCallSummary(BaseModel):
    tool_name: str
    duration_ms: int

    model_config = {"from_attributes": True}


class AgentRunResponse(BaseModel):
    id: uuid.UUID
    query: str
    response: str | None
    tools_used: list[str]
    haiku_tokens: int
    sonnet_tokens: int
    cost_usd: float
    created_at: datetime

    model_config = {"from_attributes": True}
