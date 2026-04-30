"""
One-time script to pre-populate the airport entity cache.
Costs exactly 1 API call per airport listed in AIRPORTS_TO_SEED.
Run this once; after that every flight search reuses the cached IDs.

Usage:
    cd backend
    PYTHONPATH=. python scripts/seed_airport_cache.py
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

CACHE_PATH = Path(__file__).parent.parent / "artifacts" / "airport_cache.json"
RAPIDAPI_HOST = "sky-scrapper.p.rapidapi.com"

# Add airports here whenever you hit "Airport not found: XYZ"
AIRPORTS_TO_SEED = [
    ("BEY", "Beirut"),
    ("BGW", "Baghdad"),
]


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return {k: tuple(v) for k, v in json.loads(CACHE_PATH.read_text()).items()}
        except Exception:
            pass
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache))


def pick_best(items: list, iata: str):
    def extract(item):
        nav = item.get("navigation", {})
        fp = nav.get("relevantFlightParams", {})
        sky_id = fp.get("skyId") or item.get("skyId", "")
        entity_id = fp.get("entityId") or nav.get("entityId", "")
        return (sky_id, entity_id) if sky_id and entity_id else None

    for item in items:
        r = extract(item)
        if r and r[0].upper() == iata.upper():
            return r
    for item in items:
        if item.get("navigation", {}).get("entityType") == "AIRPORT":
            r = extract(item)
            if r:
                return r
    for item in items:
        r = extract(item)
        if r:
            return r
    return None


async def resolve(iata: str, city: str, api_key: str) -> tuple | None:
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": RAPIDAPI_HOST}

    for query in [iata, city]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://{RAPIDAPI_HOST}/api/v1/flights/searchAirport",
                    headers=headers,
                    params={"query": query, "locale": "en-US"},
                )
                r.raise_for_status()
                items = r.json().get("data", [])
                result = pick_best(items, iata)
                if result:
                    print(f"  ✓ {iata} resolved via query='{query}': skyId={result[0]}, entityId={result[1]}")
                    return result
                print(f"  – query='{query}' returned {len(items)} items but none matched {iata}")
        except httpx.HTTPStatusError as exc:
            print(f"  ✗ query='{query}' failed: HTTP {exc.response.status_code}")
        except Exception as exc:
            print(f"  ✗ query='{query}' failed: {exc}")

    return None


async def main():
    # Read API key from .env
    env_path = Path(__file__).parent.parent / ".env"
    api_key = None
    for line in env_path.read_text().splitlines():
        if line.upper().startswith("RAPIDAPI_KEY="):
            api_key = line.split("=", 1)[1].strip()
            break

    if not api_key:
        print("ERROR: RAPIDAPI_KEY not found in backend/.env")
        sys.exit(1)

    cache = load_cache()
    print(f"Existing cache: {len(cache)} airports\n")

    added = 0
    for iata, city in AIRPORTS_TO_SEED:
        if iata in cache:
            print(f"  {iata} already cached — skipping")
            continue
        print(f"Resolving {iata} ({city})...")
        result = await resolve(iata, city, api_key)
        if result:
            cache[iata] = result
            added += 1
        else:
            print(f"  ✗ {iata} could not be resolved")

    if added:
        save_cache(cache)
        print(f"\nSaved {added} new airport(s) to {CACHE_PATH}")
    else:
        print("\nNothing new to save.")


if __name__ == "__main__":
    asyncio.run(main())
