"""
ML Classifier Tool
------------------
Wraps ml.inference.classify_query() as a LangChain BaseTool subclass.
Stateless — no DB session needed. Model loaded once via lru_cache in inference.py.
"""

import json
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ml.inference import classify_query


class ClassifierInput(BaseModel):
    text: str = Field(description="The destination description or user query to classify.")
    country: str = Field(default="Unknown", description="Country name for geographic context.")
    avg_cost_per_day: float = Field(default=100.0, description="Estimated daily budget in USD.")
    family_friendly: int = Field(default=0, description="1 if travelling with children, 0 otherwise.")


class MLClassifierTool(BaseTool):
    name: str = "ml_classifier"
    description: str = (
        "Classify a destination or travel query into one of six travel styles: "
        "Adventure, Relaxation, Culture, Budget, Luxury, or Family. "
        "Use this tool first to understand what kind of travel the user is describing "
        "before searching the knowledge base. If confidence is below 0.5, treat it as ambiguous."
    )
    args_schema: Type[BaseModel] = ClassifierInput

    def _run(
        self,
        text: str,
        country: str = "Unknown",
        avg_cost_per_day: float = 100.0,
        family_friendly: int = 0,
    ) -> str:
        result = classify_query(
            text=text,
            country=country,
            avg_cost_per_day=avg_cost_per_day,
            family_friendly=family_friendly,
        )
        return json.dumps(result)

    async def _arun(
        self,
        text: str,
        country: str = "Unknown",
        avg_cost_per_day: float = 100.0,
        family_friendly: int = 0,
    ) -> str:
        # classify_query is CPU-bound (sklearn) — sync call is fine inside async context
        return self._run(text, country, avg_cost_per_day, family_friendly)


ml_classifier = MLClassifierTool()
