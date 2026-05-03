"""
RAG Ingestion
-------------
Reads rag_documents/destinations.json, embeds each document with all-MiniLM-L6-v2,
and bulk-inserts into the document_chunks table.

Called once at app startup (via main.py lifespan) if the table is empty.
Safe to call again — the guard at the top skips if rows already exist.

Can also be run standalone:
    python -m app.rag.ingestion
"""

import asyncio
import json
from pathlib import Path

import structlog
from sqlalchemy import func, select

from app.db.session import AsyncSessionFactory
from app.database.db import DocumentChunk
from app.rag.embedder import embed_batch

log = structlog.get_logger()

DOCS_PATH = Path(__file__).parent.parent.parent / "rag_documents" / "destinations.json"


async def ingest_documents() -> None:
    """
    Main entry point called by the app lifespan.
    Inserts all destination documents if the table is empty.
    """
    async with AsyncSessionFactory() as session:
        # Guard: skip if already populated
        count_result = await session.execute(select(func.count()).select_from(DocumentChunk))
        existing = count_result.scalar_one()
        if existing > 0:
            log.info("rag.ingestion.skipped", existing_rows=existing)
            return

        log.info("rag.ingestion.starting", docs_path=str(DOCS_PATH))

        if not DOCS_PATH.exists():
            log.error(
                "rag.ingestion.missing_file",
                path=str(DOCS_PATH),
                hint="Run: python -m scripts.fetch_wikivoyage",
            )
            return

        raw: list[dict] = json.loads(DOCS_PATH.read_text(encoding="utf-8"))
        log.info("rag.ingestion.loaded", doc_count=len(raw))

        # Embed all content strings in one batched forward pass
        texts = [doc["content"] for doc in raw]
        embeddings = embed_batch(texts)

        chunks = [
            DocumentChunk(
                destination=doc["destination"],
                travel_style=doc["travel_style"],
                doc_type=doc["doc_type"],
                content=doc["content"],
                source=doc.get("source", "Wikivoyage"),
                embedding=embedding,
            )
            for doc, embedding in zip(raw, embeddings)
        ]

        session.add_all(chunks)
        await session.commit()

        log.info("rag.ingestion.complete", inserted=len(chunks))


if __name__ == "__main__":
    asyncio.run(ingest_documents())
