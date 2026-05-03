"""
RAG Retriever
-------------
Embeds a query string and retrieves the top-K most similar document chunks
from pgvector using cosine distance.

Travel style filtering rule (agreed):
  - If ML classifier confidence > 0.7  →  filter WHERE travel_style = <label>
  - Otherwise                           →  search all rows (broader, handles ambiguity)
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.db import DocumentChunk
from app.rag.embedder import embed

log = structlog.get_logger()

ML_CONFIDENCE_THRESHOLD = 0.7


async def retrieve(
    query: str,
    session: AsyncSession,
    travel_style: str | None = None,
    ml_confidence: float = 0.0,
    top_k: int | None = None,
) -> list[dict]:
    """
    Return the top-K chunks most similar to `query`.

    Args:
        query:          The user's natural-language query.
        session:        AsyncSession injected by the caller.
        travel_style:   ML classifier top label (e.g. "Adventure").
        ml_confidence:  ML classifier confidence score (0–1).
        top_k:          Number of results; defaults to settings.rag_top_k.

    Returns:
        List of dicts with keys: destination, travel_style, doc_type, content, source, score.
    """
    settings = get_settings()
    k = top_k or settings.rag_top_k

    query_vec = embed(query)

    stmt = select(
        DocumentChunk,
        # cosine_distance returns 0 (identical) → 2 (opposite); lower is better
        DocumentChunk.embedding.cosine_distance(query_vec).label("distance"),
    )

    # Apply travel style filter only when the ML model is confident
    if travel_style and ml_confidence > ML_CONFIDENCE_THRESHOLD:
        stmt = stmt.where(DocumentChunk.travel_style == travel_style)
        log.info(
            "rag.retriever.filtered",
            travel_style=travel_style,
            confidence=ml_confidence,
        )
    else:
        log.info(
            "rag.retriever.unfiltered",
            travel_style=travel_style,
            confidence=ml_confidence,
            reason="confidence below threshold" if travel_style else "no style label",
        )

    stmt = stmt.order_by("distance").limit(k)

    result = await session.execute(stmt)
    rows = result.all()

    chunks = []
    for chunk, distance in rows:
        chunks.append(
            {
                "destination": chunk.destination,
                "travel_style": chunk.travel_style,
                "doc_type": chunk.doc_type,
                "content": chunk.content,
                "source": chunk.source,
                "score": round(1 - distance, 4),  # convert distance → similarity (higher = better)
            }
        )

    log.info("rag.retriever.results", returned=len(chunks), top_score=chunks[0]["score"] if chunks else None)
    return chunks
