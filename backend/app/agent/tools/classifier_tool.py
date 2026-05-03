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

from classifier.inference import classify_query

#pydantic model for the classifier input's structure
class ClassifierInput(BaseModel):
    text: str = Field(description="The destination description or user query to classify.")
    country: str = Field(default="Unknown", description="Country name for geographic context.")
    avg_cost_per_day: float = Field(default=100.0, description="Estimated daily budget in USD.")
    family_friendly: int = Field(default=0, description="1 if travelling with children, 0 otherwise.")

#This turns your ML function into a LangChain tool.
class MLClassifierTool(BaseTool):
    name: str = "ml_classifier"
    description: str = ( #This is what the LLM reads to decide WHEN to use it
        "Classify a destination or travel query into one of six travel styles: "
        "Adventure, Relaxation, Culture, Budget, Luxury, or Family. "
        "Use this tool first to understand what kind of travel the user is describing "
        "before searching the knowledge base. If confidence is below 0.5, treat it as ambiguous."
    )
    args_schema: Type[BaseModel] = ClassifierInput # tells langchain These are the valid inputs for this tool

    #This is the actual ML call.
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
        return json.dumps(result) #converts Python dict → string so LLM can read it

    async def _arun(
        self,
        text: str,
        country: str = "Unknown",
        avg_cost_per_day: float = 100.0,
        family_friendly: int = 0,
    ) -> str:
        # LangGraph runs async so LangChain calls _arun, not _run.
        # _arun must exist or the tool raises NotImplementedError at runtime.
        # classify_query is pure CPU work (sklearn) — nothing to await — so we delegate to _run.
        return self._run(text, country, avg_cost_per_day, family_friendly)


ml_classifier = MLClassifierTool()
