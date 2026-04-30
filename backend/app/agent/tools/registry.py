"""
Tool registry — single source of truth for all agent tools.

- Static tools are imported directly.
- Session-dependent tools (rag_retriever) are registered as factories
  and resolved at runtime via build_tools().
- ALLOWED_TOOLS is derived automatically so it never drifts out of sync.
"""

from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.classifier_tool import ml_classifier
from app.agent.tools.weather_tool import weather
from app.agent.tools.currency_tool import currency
from app.agent.tools.rag_tool import make_rag_tool

# Static tools available immediately
_STATIC_TOOLS = [ml_classifier, weather, currency]

# Session-dependent tool factories: name → factory(session) → tool
#tools that need a DB session (rag_retriever) stored as a factory dict
_SESSION_TOOL_FACTORIES: dict[str, Callable[[AsyncSession], object]] = {
    "rag_retriever": make_rag_tool,
}

# Derived from static tools + factory keys — always in sync
ALLOWED_TOOLS: frozenset[str] = frozenset(
    [t.name for t in _STATIC_TOOLS] + list(_SESSION_TOOL_FACTORIES.keys())
)


def build_tools(session: AsyncSession) -> list:
    """Return all tools for one agent run, injecting the DB session."""
    session_tools = [factory(session) for factory in _SESSION_TOOL_FACTORIES.values()]
    return _STATIC_TOOLS + session_tools
