"""
Currency Tool
-------------
Fetches live exchange rates via Frankfurter API (ECB rates, free, no key).
"""

import json
from typing import Type

import httpx
import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

log = structlog.get_logger()

# Turns country name → currency code
COUNTRY_CURRENCY: dict[str, str] = {
    "New Zealand": "NZD", "Argentina": "ARS", "Indonesia": "IDR",
    "Greece": "EUR", "Japan": "JPY", "Italy": "EUR", "Thailand": "THB",
    "Portugal": "EUR", "USA": "USD", "Singapore": "SGD", "France": "EUR",
    "Spain": "EUR", "Germany": "EUR", "United Kingdom": "GBP",
    "Australia": "AUD", "Canada": "CAD", "India": "INR", "China": "CNY",
    "Brazil": "BRL", "Mexico": "MXN", "South Africa": "ZAR", "Turkey": "TRY",
    "Philippines": "PHP", "Malaysia": "MYR", "South Korea": "KRW",
    "Switzerland": "CHF", "Sweden": "SEK", "Norway": "NOK", "Denmark": "DKK",
    "Hong Kong": "HKD", "Israel": "ILS", "Hungary": "HUF",
    "Czech Republic": "CZK", "Romania": "RON", "Iceland": "ISK",
    "Vietnam": "VND",
}

#retry: If API fails → try again up to 3 times. Wait longer each retry
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
            return None
        resp.raise_for_status()
        return resp.json()


class CurrencyInput(BaseModel):
    country: str = Field(description="The destination country name. Must always be provided. Examples: 'Thailand', 'Japan', 'Italy'.")
    base_currency: str = Field(default="USD", description="The traveller's home currency code (e.g. 'USD').")


class CurrencyTool(BaseTool):
    name: str = "currency"
    description: str = (
        "Get the live exchange rate between the traveller's home currency and the "
        "destination country's currency. Use this when the user asks about costs, "
        "how far their money goes, or currency conversion."
    )
    args_schema: Type[BaseModel] = CurrencyInput

    def _run(self, country: str, base_currency: str = "USD") -> str:
        try:
            target_currency = COUNTRY_CURRENCY.get(country)
            if not target_currency:
                return json.dumps({"error": f"No currency mapping for '{country}'."})
            raw = _fetch_exchange(base_currency, target_currency)
            if not raw:
                return json.dumps({"error": f"{target_currency} is not available in ECB data."})
            rate = raw["rates"].get(target_currency)
            return json.dumps({
                "base": base_currency,
                "target": target_currency,
                "rate": rate,
                "source": "Frankfurter (ECB)",
            })
        except Exception as exc:
            log.warning("currency_tool.error", error=str(exc))
            return json.dumps({"error": f"Exchange rate fetch failed: {exc}"})

    async def _arun(self, country: str, base_currency: str = "USD") -> str:
        return self._run(country, base_currency)


currency = CurrencyTool()
