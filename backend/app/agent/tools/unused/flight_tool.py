"""
Flight Search Tool
------------------
Lets the agent search for live flight prices via Sky Scrapper (Skyscanner data).
Reuses the airport entity resolution and search logic from app.api.flights.
"""

import json
from typing import Type

import httpx
import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.api.flights import CITY_TO_IATA, RAPIDAPI_HOST, _get_airport_entity, city_to_iata
from app.config import get_settings

log = structlog.get_logger()


class FlightSearchInput(BaseModel):
    origin: str = Field(description="Origin city name or IATA code (e.g. 'London' or 'LHR').")
    destination: str = Field(description="Destination city name or IATA code (e.g. 'Bali' or 'DPS').")
    date: str = Field(description="Departure date in YYYY-MM-DD format.")
    adults: int = Field(default=1, ge=1, le=9, description="Number of adult passengers.")


class FlightSearchTool(BaseTool):
    name: str = "flight_search"
    description: str = (
        "Search for live flight prices between two cities or airports. "
        "Use this when the user asks about flights, flight costs, or wants to know "
        "how to get to a destination. Returns up to 5 cheapest options with price, "
        "airline, stops, and duration."
    )
    args_schema: Type[BaseModel] = FlightSearchInput

    def _run(self, origin: str, destination: str, date: str, adults: int = 1) -> str:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._async_search(origin, destination, date, adults))
                    return future.result()
        except RuntimeError:
            pass
        return asyncio.run(self._async_search(origin, destination, date, adults))

    async def _arun(self, origin: str, destination: str, date: str, adults: int = 1) -> str:
        return await self._async_search(origin, destination, date, adults)

    async def _async_search(self, origin: str, destination: str, date: str, adults: int) -> str:
        settings = get_settings()
        if not settings.rapidapi_key:
            return json.dumps({"error": "Flight search not configured (missing RAPIDAPI_KEY)."})

        # Resolve city names to IATA codes
        from_iata = city_to_iata(origin) or origin.upper()
        to_iata = city_to_iata(destination) or destination.upper()

        api_key = settings.rapidapi_key

        # Resolve IATA codes to Skyscanner entity IDs
        import asyncio
        from_info, to_info = await asyncio.gather(
            _get_airport_entity(from_iata, api_key),
            _get_airport_entity(to_iata, api_key),
        )

        if not from_info:
            return json.dumps({"error": f"Could not find airport for '{origin}' (IATA: {from_iata})."})
        if not to_info:
            return json.dumps({"error": f"Could not find airport for '{destination}' (IATA: {to_iata})."})

        from_sky_id, from_entity_id = from_info
        to_sky_id, to_entity_id = to_info

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }
        params = {
            "originSkyId": from_sky_id,
            "destinationSkyId": to_sky_id,
            "originEntityId": from_entity_id,
            "destinationEntityId": to_entity_id,
            "date": date,
            "adults": adults,
            "currency": "USD",
            "locale": "en-US",
            "market": "US",
            "cabinClass": "economy",
            "countryCode": "US",
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(
                    f"https://{RAPIDAPI_HOST}/api/v2/flights/searchFlights",
                    headers=headers,
                    params=params,
                )
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                return json.dumps({"error": "Flight search quota exceeded. The free RapidAPI plan limit has been reached — upgrade at rapidapi.com or try again next month."})
            log.error("flight_tool.search_error", status=exc.response.status_code)
            return json.dumps({"error": f"Flight search failed: {exc.response.status_code}"})
        except Exception as exc:
            log.error("flight_tool.search_error", error=str(exc))
            return json.dumps({"error": f"Flight search failed: {exc}"})

        itineraries = data.get("data", {}).get("itineraries", [])
        if not itineraries:
            log.warning(
                "flight_tool.no_itineraries",
                from_iata=from_iata,
                to_iata=to_iata,
                date=date,
                api_status=data.get("status"),
                context=data.get("data", {}).get("context"),
            )
            return json.dumps({
                "flights": [],
                "message": f"No flights found from {origin} to {destination} on {date}.",
            })

        flights = []
        for it in itineraries[:5]:
            price = it.get("price", {}).get("raw", 0)
            legs = it.get("legs", [])
            if not legs:
                continue
            leg = legs[0]
            carriers = leg.get("carriers", {}).get("marketing", [{}])
            airline = carriers[0].get("name", "?") if carriers else "?"
            stops = leg.get("stopCount", 0)
            mins = leg.get("durationInMinutes", 0)
            hours, remainder = divmod(mins, 60)
            departure = leg.get("departure", "")
            flights.append({
                "price_usd": round(price, 2),
                "airline": airline,
                "stops": stops,
                "duration": f"{hours}h {remainder}m",
                "departure": departure,
            })

        flights.sort(key=lambda x: x["price_usd"])

        return json.dumps({
            "from": origin,
            "to": destination,
            "date": date,
            "adults": adults,
            "flights": flights,
            "note": "Live prices from Skyscanner via RapidAPI · economy class",
        })


flight_search = FlightSearchTool()
