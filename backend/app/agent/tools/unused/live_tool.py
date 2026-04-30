"""
Live Conditions Tool
--------------------
Fetches real-time weather (Open-Meteo — free, no API key) and exchange rates
(Frankfurter API — free, no key, ECB rates).

Weather flow:
  1. Geocode city name → lat/lon via Nominatim (OpenStreetMap)
  2. Fetch current weather from Open-Meteo using those coordinates

Both calls are independently fault-tolerant: if one fails, the other
still returns. Retries use tenacity with exponential backoff.
"""

import json
from typing import Type

import httpx
import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

log = structlog.get_logger()

# Only currencies covered by the ECB / Frankfurter API
COUNTRY_CURRENCY: dict[str, str] = {
    "New Zealand": "NZD",
    "Argentina": "ARS",
    "Indonesia": "IDR",
    "Greece": "EUR",
    "Japan": "JPY",
    "Italy": "EUR",
    "Thailand": "THB",
    "Portugal": "EUR",
    "USA": "USD",
    "Singapore": "SGD",
    "France": "EUR",
    "Spain": "EUR",
    "Germany": "EUR",
    "United Kingdom": "GBP",
    "Australia": "AUD",
    "Canada": "CAD",
    "India": "INR",
    "China": "CNY",
    "Brazil": "BRL",
    "Mexico": "MXN",
    "South Africa": "ZAR",
    "Turkey": "TRY",
    "Philippines": "PHP",
    "Malaysia": "MYR",
    "South Korea": "KRW",
    "Switzerland": "CHF",
    "Sweden": "SEK",
    "Norway": "NOK",
    "Denmark": "DKK",
    "Hong Kong": "HKD",
    "Israel": "ILS",
    "Hungary": "HUF",
    "Czech Republic": "CZK",
    "Romania": "RON",
    "Iceland": "ISK",
    "Vietnam": "VND",
}

# WMO Weather Interpretation Codes → human-readable description
WMO_CODES: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "icy fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "heavy drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "rain showers", 81: "moderate rain showers", 82: "heavy rain showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def _geocode(city: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a city name using Nominatim."""
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "AITravelPlanner/1.0"},
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def _fetch_weather(lat: float, lon: float) -> dict:
    """Fetch current weather from Open-Meteo (no API key required)."""
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,weathercode,windspeed_10m,relativehumidity_2m",
                "temperature_unit": "celsius",
                "windspeed_unit": "kmh",
            },
        )
        resp.raise_for_status()
        return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def _fetch_exchange(base: str, target: str) -> dict | None:
    if base == target:
        return {"rates": {target: 1.0}}
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"from": base, "to": target},
        )
        if resp.status_code == 404:
            return None  # currency not in ECB database — don't retry
        resp.raise_for_status()
        return resp.json()


class LiveConditionsInput(BaseModel):
    city: str = Field(description="City name for the weather lookup (e.g. 'Bangkok').")
    country: str = Field(description="Country name to determine the local currency (e.g. 'Thailand').")
    base_currency: str = Field(default="USD", description="The traveller's home currency.")


class LiveConditionsTool(BaseTool):
    name: str = "live_conditions"
    description: str = (
        "Get real-time weather and currency exchange rate for a destination. "
        "Use this when the user asks about current conditions, best time to visit, "
        "or wants to know how far their money goes at a destination."
    )
    args_schema: Type[BaseModel] = LiveConditionsInput

    def _run(self, city: str, country: str, base_currency: str = "USD") -> str:
        warnings: list[str] = []
        weather_out = None
        exchange_out = None

        # ── Weather (Open-Meteo, no API key needed) ────────────────────────────
        try:
            coords = _geocode(city)
            if not coords:
                warnings.append(f"City '{city}' not found.")
            else:
                lat, lon = coords
                raw = _fetch_weather(lat, lon)
                current = raw.get("current", {})
                code = current.get("weathercode", 0)
                weather_out = {
                    "city": city,
                    "temperature_c": current.get("temperature_2m"),
                    "feels_like_c": current.get("apparent_temperature"),
                    "description": WMO_CODES.get(code, "unknown"),
                    "humidity_pct": current.get("relativehumidity_2m"),
                    "wind_kph": current.get("windspeed_10m"),
                }
        except Exception as exc:
            log.warning("live_tool.weather.error", error=str(exc))
            warnings.append(f"Weather fetch failed: {exc}")

        # ── Exchange rate (Frankfurter / ECB) ──────────────────────────────────
        try:
            target_currency = COUNTRY_CURRENCY.get(country)
            if not target_currency:
                warnings.append(f"No currency mapping for country '{country}'.")
            else:
                raw_fx = _fetch_exchange(base_currency, target_currency)
                if raw_fx:
                    rate = raw_fx["rates"].get(target_currency)
                    if rate:
                        exchange_out = {
                            "base": base_currency,
                            "target": target_currency,
                            "rate": rate,
                            "source": "Frankfurter (ECB)",
                        }
        except Exception as exc:
            log.warning("live_tool.exchange.error", error=str(exc))
            warnings.append(f"Exchange rate fetch failed: {exc}")

        return json.dumps({"weather": weather_out, "exchange": exchange_out, "warnings": warnings})

    async def _arun(self, city: str, country: str, base_currency: str = "USD") -> str:
        return self._run(city, country, base_currency)


live_conditions = LiveConditionsTool()
