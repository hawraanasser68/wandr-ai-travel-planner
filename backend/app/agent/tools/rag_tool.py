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
    args_schema: Type[BaseModel] = RAGInput #defines expected input

    # session is stored as an instance field — injected by make_rag_tool()
    session: AsyncSession #This tool has access to the database

    #class Config tells Pydantic: "don't try to validate this field, just store whatever object I pass in.
    class Config:
        arbitrary_types_allowed = True #Because AsyncSession is not a simple type. Pydantic normally rejects it → this allows it


    #this tool is async only because database call are async. LangChain will call _arun, not _run. If _arun doesn't exist → NotImplementedError at runtime.
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
            "filtered_by_style": bool(travel_style and ml_confidence > 0.7), #Only trust classifier if confidence is high
        })


def make_rag_tool(session: AsyncSession) -> RAGRetrieverTool:
    """Return a RAGRetrieverTool bound to the given request-scoped session."""
    return RAGRetrieverTool(session=session)

# in the case of the retriever tool we did not do rag_tool = RAGRetrieverTool() because this tool needs a db session injected in it 