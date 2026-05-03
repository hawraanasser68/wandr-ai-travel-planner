"""
ML Inference Module
--------------------
Exposes classify_query() — the single function the agent tool imports.
The model and encoder are loaded once at module level (singleton pattern).
Calling classify_query() on every request does NOT reload from disk.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd

from app.config import get_settings
from classifier.transforms import flatten_text  # noqa: F401 — required for joblib unpickling


@lru_cache(maxsize=1)
def _load_artifacts() -> tuple:
    """
    Load model and label encoder once per process.
    lru_cache with maxsize=1 means subsequent calls return the cached objects.
    """
    settings = get_settings()
    model = joblib.load(settings.ml_model_path)
    encoder = joblib.load(settings.ml_encoder_path)
    return model, encoder


def classify_query(
    text: str,
    country: str = "Unknown",
    avg_cost_per_day: float = 100.0,
    family_friendly: int = 0,
) -> dict:
    """
    Classify a travel query or destination description into a travel style.

    Returns a dict with:
      - top_label      : the most likely travel style string
      - confidence     : float 0-1 for top_label
      - scores         : full probability distribution across all 6 classes

    The agent injects these scores into its system prompt so it can reason
    about ambiguous requests (e.g., query that is 55% Relaxation, 35% Culture).
    """
    model, encoder = _load_artifacts()

    # Build a single-row DataFrame matching the training feature schema
    row = pd.DataFrame([{
        "avg_cost_per_day": avg_cost_per_day,
        "family_friendly": family_friendly,
        "country": country,
        "text": text,
    }])

    # predict_proba gives calibrated probabilities (works for LR, SVM, RF)
    proba = model.predict_proba(row)[0]
    class_names = encoder.classes_  # e.g. ["Adventure", "Budget", ...]

    # Sort by probability descending
    scores = dict(sorted(
        zip(class_names, proba.tolist()),
        key=lambda x: x[1],
        reverse=True,
    ))

    top_label = list(scores.keys())[0]
    confidence = list(scores.values())[0]

    return {
        "top_label": top_label,
        "confidence": round(confidence, 4),
        "scores": {k: round(v, 4) for k, v in scores.items()},
    }
