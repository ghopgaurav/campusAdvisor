"""
Cost-of-living lookup tool.
Uses the Numbeo public API (no key needed for city queries) as the primary source,
with a lightweight web-search fallback if the city isn't found.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NUMBEO_URL = "https://www.numbeo.com/api/city_prices"

# Monthly cost index buckets (rough USD estimates based on Numbeo indices)
_MONTHLY_TEMPLATES = {
    "rent_1br_city_center": "1BR apartment in city center (monthly rent)",
    "rent_1br_outside_center": "1BR apartment outside center (monthly rent)",
    "meal_inexpensive": "Inexpensive restaurant meal",
    "meal_midrange_for_two": "Mid-range restaurant (2 people)",
    "groceries_monthly_estimate": "Monthly groceries estimate (single person)",
    "public_transport_monthly": "Monthly public transport pass",
    "utilities_monthly": "Monthly utilities (electricity, heat, water)",
    "internet_monthly": "Monthly internet (60 Mbps)",
}


async def get_cost_of_living(city: str, country: str = "United States") -> dict[str, Any]:
    """
    Return cost-of-living data for a city.

    Args:
        city: City name (e.g. "Boston").
        country: Country name (default "United States").

    Returns:
        Dict with city, country, currency, and cost items.
    """
    params = {"city": city, "country": country, "currency": "USD"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(NUMBEO_URL, params=params)

        if resp.status_code == 200:
            data = resp.json()
            prices = data.get("prices", [])

            # Map Numbeo item_id to friendly names
            # Key item IDs: 48=1BR center, 49=1BR outside, 1=meal cheap,
            # 2=meal midrange, 8=grocery, 20=transport pass, 28=utilities, 33=internet
            item_map = {
                48: "rent_1br_city_center",
                49: "rent_1br_outside_center",
                1:  "meal_inexpensive",
                2:  "meal_midrange_for_two",
                8:  "groceries_monthly_estimate",
                20: "public_transport_monthly",
                28: "utilities_monthly",
                33: "internet_monthly",
            }

            costs: dict[str, float | None] = {}
            for item in prices:
                item_id = item.get("item_id")
                if item_id in item_map:
                    costs[item_map[item_id]] = item.get("average_price")

            return {
                "city": city,
                "country": country,
                "currency": "USD",
                "source": "Numbeo",
                "costs": costs,
                "descriptions": _MONTHLY_TEMPLATES,
                "note": "Prices are averages and may vary. Verify with local listings.",
            }

    except Exception as exc:
        logger.warning("Numbeo lookup failed for %s, %s: %s", city, country, exc)

    # Fallback: indicate data unavailable so the agent can web-search instead
    return {
        "city": city,
        "country": country,
        "currency": "USD",
        "source": None,
        "costs": {},
        "error": f"Could not retrieve cost-of-living data for {city}. Try a web search.",
    }
