"""
Tool I/O schemas — Pydantic models for each agent tool's input and output.

The LangGraph tool nodes validate incoming args against these models before
executing any logic, so malformed LLM-generated args are caught early and
returned as a structured error instead of crashing the graph.
"""

from pydantic import BaseModel, Field


# ── RAG retriever tool ─────────────────────────────────────────────────────────

class RAGToolInput(BaseModel):
    query: str = Field(description="The travel question or topic to search for")
    travel_style: str | None = Field(
        default=None,
        description="Filter results by style (Adventure, Relaxation, Culture, Budget, Luxury, Family)",
    )
    ml_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="ML classifier confidence — used to decide whether to apply the style filter",
    )


class RAGChunk(BaseModel):
    destination: str
    travel_style: str
    doc_type: str
    content: str
    source: str
    score: float


class RAGToolOutput(BaseModel):
    chunks: list[RAGChunk]
    filtered_by_style: bool


# ── ML classifier tool ─────────────────────────────────────────────────────────

class ClassifierToolInput(BaseModel):
    text: str = Field(description="Destination description or user query to classify")
    country: str = Field(default="Unknown")
    avg_cost_per_day: float = Field(default=100.0, ge=0)
    family_friendly: int = Field(default=0, ge=0, le=1)


class ClassifierToolOutput(BaseModel):
    top_label: str
    confidence: float
    scores: dict[str, float]  # full probability distribution across all 6 classes


# ── Live conditions tool ───────────────────────────────────────────────────────

class LiveConditionsInput(BaseModel):
    city: str = Field(description="City name for weather lookup")
    country: str = Field(description="Country name for exchange rate lookup (e.g. 'Japan')")
    base_currency: str = Field(
        default="USD",
        description="Currency to convert FROM (traveller's home currency)",
    )


class WeatherInfo(BaseModel):
    city: str
    temperature_c: float
    feels_like_c: float
    description: str       # e.g. "clear sky", "light rain"
    humidity_pct: int
    wind_kph: float


class ExchangeInfo(BaseModel):
    base: str              # e.g. "USD"
    target: str            # e.g. "JPY"
    rate: float            # 1 USD = rate JPY
    source: str            # e.g. "Open Exchange Rates"


class LiveConditionsOutput(BaseModel):
    weather: WeatherInfo | None         # None if city not found or API down
    exchange: ExchangeInfo | None       # None if country currency unknown or API down
    warnings: list[str] = []            # non-fatal issues (e.g. "weather API unavailable")
