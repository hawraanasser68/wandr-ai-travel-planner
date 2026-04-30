"""
Weather Tool
------------
Fetches real-time weather via Open-Meteo (free, no API key).

Flow:
  1. Geocode city name → lat/lon via Nominatim (OpenStreetMap)
  2. Fetch current conditions from Open-Meteo
"""

import json
from typing import Type

import httpx
import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

log = structlog.get_logger()

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


class WeatherInput(BaseModel):
    city: str = Field(description="The city name to fetch weather for. Must always be provided. Examples: 'Bangkok', 'Bali', 'Dubai'.")


class WeatherTool(BaseTool):
    name: str = "weather"
    description: str = (
        "Get real-time weather conditions for a destination city. "
        "Use this when the user asks about current weather, best time to visit, "
        "or what to pack."
    )
    args_schema: Type[BaseModel] = WeatherInput

    def _run(self, city: str) -> str:
        try:
            coords = _geocode(city)
            if not coords:
                return json.dumps({"error": f"City '{city}' not found."})
            lat, lon = coords
            raw = _fetch_weather(lat, lon)
            current = raw.get("current", {})
            code = current.get("weathercode", 0)
            return json.dumps({
                "city": city,
                "temperature_c": current.get("temperature_2m"),
                "feels_like_c": current.get("apparent_temperature"),
                "description": WMO_CODES.get(code, "unknown"),
                "humidity_pct": current.get("relativehumidity_2m"),
                "wind_kph": current.get("windspeed_10m"),
            })
        except Exception as exc:
            log.warning("weather_tool.error", error=str(exc))
            return json.dumps({"error": f"Weather fetch failed: {exc}"})

    async def _arun(self, city: str) -> str:
        return self._run(city)


weather = WeatherTool()
