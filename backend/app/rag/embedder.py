"""
Singleton wrapper around SentenceTransformer.
Loaded once per process via lru_cache — both ingestion and retriever import from here.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model)


def embed(text: str) -> list[float]:
    """Embed a single string, return as a plain Python list (pgvector expects list[float])."""
    model = get_embedder()
    vector: np.ndarray = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings in one forward pass — more efficient for ingestion."""
    model = get_embedder()
    vectors: np.ndarray = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return vectors.tolist()
