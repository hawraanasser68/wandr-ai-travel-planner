"""
RAG Retriever Tool
------------------
BaseTool subclass that queries pgvector for relevant destination knowledge.

Why a factory? BaseTool instances are created once, but the DB session is
request-scoped. make_rag_tool(session) returns a new tool instance per request
with the session captured as an instance field.
"""

import json
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.retriever import retrieve


class RAGInput(BaseModel):
    query: str = Field(description="What you want to know (e.g. 'budget tips for Bangkok').")
    travel_style: str | None = Field(default=None, description="The ML classifier's top label (e.g. 'Adventure').")
    ml_confidence: float = Field(default=0.0, description="The classifier's confidence score (0–1).")


class RAGRetrieverTool(BaseTool):
    name: str = "rag_retriever"
    description: str = (
        "Search the travel knowledge base for relevant destination information. "
        "Use this to find facts about destinations: what to do, practical tips, "
        "costs, best seasons, and local culture. Always call after the classifier "
        "so you can pass travel_style and ml_confidence for targeted results."
    )
    args_schema: Type[BaseModel] = RAGInput

    # session is stored as an instance field — injected by make_rag_tool()
    session: AsyncSession

    class Config:
        arbitrary_types_allowed = True

    def _run(self, query: str, travel_style: str | None = None, ml_confidence: float = 0.0) -> str:
        raise NotImplementedError("RAGRetrieverTool is async-only. Use _arun.")

    async def _arun(self, query: str, travel_style: str | None = None, ml_confidence: float = 0.0) -> str:
        chunks = await retrieve(
            query=query,
            session=self.session,
            travel_style=travel_style,
            ml_confidence=ml_confidence,
        )

        if not chunks:
            return json.dumps({"results": [], "message": "No matching documents found."})

        formatted = [
            f"[{c['destination']} – {c['doc_type']}] (score: {c['score']})\n{c['content']}"
            for c in chunks
        ]
        return json.dumps({
            "results": formatted,
            "filtered_by_style": bool(travel_style and ml_confidence > 0.7),
        })


def make_rag_tool(session: AsyncSession) -> RAGRetrieverTool:
    """Return a RAGRetrieverTool bound to the given request-scoped session."""
    return RAGRetrieverTool(session=session)
