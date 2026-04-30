"""
Flight Search API
-----------------
GET /flights/search  — queries Sky Scrapper (Skyscanner data) via RapidAPI
GET /flights/iata    — resolves a city name to an IATA code (frontend helper)

Requires RAPIDAPI_KEY in .env.
Subscribe free at rapidapi.com → search "Sky Scrapper".
"""

import json
import time
from pathlib import Path

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.dependencies import get_current_user
from app.models.db import User

log = structlog.get_logger()
router = APIRouter(prefix="/flights", tags=["flights"])

RAPIDAPI_HOST = "sky-scrapper.p.rapidapi.com"

# Airport entity cache — persisted to disk so it survives server restarts.
# Each lookup costs 1 API call; with ~100 airports this saves significant quota.
_AIRPORT_CACHE_PATH = Path(__file__).parent.parent.parent / "artifacts" / "airport_cache.json"
_airport_cache: dict[str, tuple[str, str]] = {}


def _load_airport_cache() -> None:
    if _AIRPORT_CACHE_PATH.exists():
        try:
            raw = json.loads(_AIRPORT_CACHE_PATH.read_text())
            _airport_cache.update({k: tuple(v) for k, v in raw.items()})
            log.info("flights.airport_cache_loaded", entries=len(_airport_cache))
        except Exception:
            pass


def _save_airport_cache() -> None:
    try:
        _AIRPORT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _AIRPORT_CACHE_PATH.write_text(json.dumps(_airport_cache))
    except Exception as exc:
        log.warning("flights.airport_cache_save_failed", error=str(exc))


_load_airport_cache()

# Flight results cache — 30-minute TTL to avoid burning quota on repeated searches.
# Key: (from_iata, to_iata, date, adults)  Value: (timestamp, result_dict)
_FLIGHT_CACHE_TTL = 1800  # 30 minutes
_flight_cache: dict[tuple, tuple[float, dict]] = {}

CITY_TO_IATA: dict[str, str] = {
    "bali": "DPS", "denpasar": "DPS",
    "tokyo": "NRT", "kyoto": "KIX", "osaka": "KIX",
    "santorini": "JTR", "athens": "ATH",
    "dubai": "DXB", "abu dhabi": "AUH",
    "maldives": "MLE", "male": "MLE",
    "bangkok": "BKK",
    "lisbon": "LIS",
    "florence": "FLR",
    "queenstown": "ZQN", "christchurch": "CHC",
    "singapore": "SIN",
    "marrakech": "RAK",
    "phuket": "HKT",
    "costa rica": "SJO", "san jose": "SJO",
    "patagonia": "PMC", "puerto montt": "PMC",
    "london": "LHR", "heathrow": "LHR",
    "paris": "CDG",
    "new york": "JFK", "nyc": "JFK",
    "los angeles": "LAX",
    "sydney": "SYD",
    "amsterdam": "AMS",
    "frankfurt": "FRA",
    "madrid": "MAD",
    "rome": "FCO",
    "milan": "MXP",
    "barcelona": "BCN",
    "istanbul": "IST",
    "hong kong": "HKG",
    "shanghai": "PVG",
    "beijing": "PEK",
    "toronto": "YYZ",
    "chicago": "ORD",
    "miami": "MIA",
    "berlin": "BER",
    "vienna": "VIE",
    "brussels": "BRU",
    "zurich": "ZRH",
    "stockholm": "ARN",
    "oslo": "OSL",
    "copenhagen": "CPH",
    "helsinki": "HEL",
    "cairo": "CAI",
    "johannesburg": "JNB",
    "nairobi": "NBO",
    "mumbai": "BOM",
    "delhi": "DEL",
    "kuala lumpur": "KUL",
    "jakarta": "CGK",
    "seoul": "ICN",
    "taipei": "TPE",
    "doha": "DOH",
    "riyadh": "RUH",
    "baghdad": "BGW",
    "beirut": "BEY",
    "kuwait": "KWI",
    "muscat": "MCT",
    "lahore": "LHE",
    "karachi": "KHI",
    "colombo": "CMB",
    "kathmandu": "KTM",
    "dhaka": "DAC",
    "yangon": "RGN",
    "ho chi minh": "SGN", "saigon": "SGN",
    "hanoi": "HAN",
    "manila": "MNL",
    "auckland": "AKL",
    "melbourne": "MEL",
    "brisbane": "BNE",
    "cape town": "CPT",
    "lagos": "LOS",
    "accra": "ACC",
    "casablanca": "CMN",
    "tunis": "TUN",
    "algiers": "ALG",
    "montreal": "YUL",
    "vancouver": "YVR",
    "mexico city": "MEX",
    "cancun": "CUN",
    "lima": "LIM",
    "bogota": "BOG",
    "buenos aires": "EZE",
    "sao paulo": "GRU",
    "rio de janeiro": "GIG",
    "santiago": "SCL",
    # Countries → main airport
    "iraq": "BGW", "indonesia": "CGK", "japan": "NRT",
    "greece": "ATH", "thailand": "BKK", "portugal": "LIS",
    "italy": "FCO", "france": "CDG", "spain": "MAD",
    "germany": "FRA", "netherlands": "AMS", "turkey": "IST",
    "australia": "SYD", "new zealand": "AKL", "canada": "YYZ",
    "usa": "JFK", "united states": "JFK",
    "united kingdom": "LHR", "uk": "LHR", "england": "LHR",
    "india": "DEL", "china": "PEK",
    "south korea": "ICN", "korea": "ICN",
    "malaysia": "KUL", "philippines": "MNL", "vietnam": "HAN",
    "colombia": "BOG", "peru": "LIM", "argentina": "EZE",
    "brazil": "GRU", "chile": "SCL", "mexico": "MEX",
    "egypt": "CAI", "kenya": "NBO", "south africa": "JNB",
    "morocco": "CMN", "qatar": "DOH",
    "uae": "DXB", "united arab emirates": "DXB",
    "saudi arabia": "RUH", "jordan": "AMM", "lebanon": "BEY",
    "kuwait city": "KWI", "oman": "MCT", "bahrain": "BAH",
    "pakistan": "KHI", "sri lanka": "CMB", "nepal": "KTM",
    "switzerland": "ZRH", "austria": "VIE", "belgium": "BRU",
    "sweden": "ARN", "norway": "OSL", "denmark": "CPH",
    "finland": "HEL",
}


def city_to_iata(city: str) -> str | None:
    return CITY_TO_IATA.get(city.strip().lower())


# Reverse map: IATA → preferred city name for fallback airport search.
# Sky Scrapper returns empty results for some IATA codes (especially Middle East)
# but finds them fine when queried by city name.
_IATA_TO_CITY: dict[str, str] = {}
for _city, _code in CITY_TO_IATA.items():
    if _code not in _IATA_TO_CITY:  # keep the first (most specific) city name
        _IATA_TO_CITY[_code] = _city.title()


async def _search_airport_query(query: str, api_key: str) -> list[dict]:
    """Call Sky Scrapper searchAirport and return the data array (empty on failure)."""
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": RAPIDAPI_HOST}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://{RAPIDAPI_HOST}/api/v1/flights/searchAirport",
                headers=headers,
                params={"query": query, "locale": "en-US"},
            )
            r.raise_for_status()
            return r.json().get("data", [])
    except Exception as exc:
        log.warning("flights.airport_lookup_failed", query=query, error=str(exc))
        return []


def _extract_entity(item: dict) -> tuple[str, str] | None:
    nav = item.get("navigation", {})
    fp = nav.get("relevantFlightParams", {})
    sky_id = fp.get("skyId") or item.get("skyId", "")
    entity_id = fp.get("entityId") or nav.get("entityId", "")
    if sky_id and entity_id:
        return sky_id, entity_id
    return None


def _pick_best(items: list[dict], iata: str) -> tuple[str, str] | None:
    """Three-pass selection: exact skyId match → first AIRPORT → first of any type."""
    for item in items:
        r = _extract_entity(item)
        if r and r[0].upper() == iata.upper():
            return r
    for item in items:
        if item.get("navigation", {}).get("entityType") == "AIRPORT":
            r = _extract_entity(item)
            if r:
                return r
    for item in items:
        r = _extract_entity(item)
        if r:
            return r
    return None


async def _get_airport_entity(iata: str, api_key: str) -> tuple[str, str] | None:
    """Return (skyId, entityId) for an IATA code, with city-name fallback."""
    if iata in _airport_cache:
        return _airport_cache[iata]

    # Try IATA code first
    items = await _search_airport_query(iata, api_key)
    result = _pick_best(items, iata)

    # If IATA search returned nothing useful, retry with the city name
    if not result:
        city_name = _IATA_TO_CITY.get(iata.upper())
        if city_name:
            log.info("flights.airport_fallback_to_city", iata=iata, city=city_name)
            items = await _search_airport_query(city_name, api_key)
            result = _pick_best(items, iata)
            # city search won't have an exact IATA match — accept the best result
            if not result and items:
                result = _extract_entity(items[0])

    if result:
        _airport_cache[iata] = result
        _save_airport_cache()
        return result

    log.warning("flights.airport_not_found", iata=iata)
    return None


@router.get("/iata")
def resolve_iata(city: str = Query(...)) -> dict:
    """Resolve a city name to its IATA airport code."""
    code = city_to_iata(city)
    if not code:
        raise HTTPException(status_code=404, detail=f"No IATA code found for '{city}'")
    return {"city": city, "iata": code}


@router.get("/search")
async def search_flights(
    from_iata: str = Query(..., min_length=2, max_length=3),
    to_iata: str = Query(..., min_length=2, max_length=3),
    date: str = Query(..., description="Departure date YYYY-MM-DD"),
    adults: int = Query(default=1, ge=1, le=9),
    _user: User = Depends(get_current_user),
) -> dict:
    """
    Search live flight prices via Sky Scrapper (Skyscanner data) on RapidAPI.
    Returns up to 5 options sorted by price (cheapest first).
    """
    settings = get_settings()
    if not settings.rapidapi_key:
        raise HTTPException(
            status_code=503,
            detail="Flight API not configured. Add RAPIDAPI_KEY to .env",
        )

    api_key = settings.rapidapi_key
    from_iata = from_iata.upper()
    to_iata = to_iata.upper()

    # Return cached result if still fresh
    cache_key = (from_iata, to_iata, date, adults)
    cached = _flight_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < _FLIGHT_CACHE_TTL:
        log.info("flights.cache_hit", from_iata=from_iata, to_iata=to_iata, date=date)
        return cached[1]

    # Resolve IATA codes to Skyscanner entity IDs (parallel lookups)
    import asyncio
    from_info, to_info = await asyncio.gather(
        _get_airport_entity(from_iata, api_key),
        _get_airport_entity(to_iata, api_key),
    )

    if not from_info:
        raise HTTPException(status_code=422, detail=f"Airport not found: {from_iata}")
    if not to_info:
        raise HTTPException(status_code=422, detail=f"Airport not found: {to_iata}")

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
        log.error("flights.search_error", status=exc.response.status_code)
        if exc.response.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Flight search quota exceeded. The free RapidAPI plan has a monthly limit — upgrade at rapidapi.com or try again next month.",
            )
        raise HTTPException(status_code=502, detail=f"Flight search failed: {exc.response.status_code}")
    except Exception as exc:
        log.error("flights.search_error", error=str(exc))
        raise HTTPException(status_code=502, detail="Flight search failed")

    itineraries = data.get("data", {}).get("itineraries", [])
    if not itineraries:
        log.warning(
            "flights.no_itineraries",
            from_iata=from_iata,
            to_iata=to_iata,
            date=date,
            api_status=data.get("status"),
            api_message=data.get("message"),
            context=data.get("data", {}).get("context"),
        )
        return {"flights": [], "message": "No flights found for this route and date."}

    flights = []
    for it in itineraries[:5]:
        price = it.get("price", {}).get("raw", 0)
        legs = it.get("legs", [])
        if not legs:
            continue
        leg = legs[0]
        carriers = leg.get("carriers", {}).get("marketing", [{}])
        airline_code = carriers[0].get("alternateId", "?") if carriers else "?"
        airline_name = carriers[0].get("name", airline_code) if carriers else airline_code
        stops = leg.get("stopCount", 0)
        duration_minutes = leg.get("durationInMinutes", 0)
        hours, mins = divmod(duration_minutes, 60)
        departure = leg.get("departure", "")

        flights.append({
            "price_usd": round(price, 2),
            "airline": airline_name,
            "stops": stops,
            "duration": f"{hours}h {mins}m",
            "departure": departure,
        })

    flights.sort(key=lambda x: x["price_usd"])

    result = {
        "from": from_iata,
        "to": to_iata,
        "date": date,
        "adults": adults,
        "flights": flights,
        "note": "Live prices from Skyscanner via RapidAPI · economy class",
    }
    _flight_cache[cache_key] = (time.time(), result)
    return result
