"""
College Scorecard API tool.
Docs: https://collegescorecard.ed.gov/data/documentation/
Free API key: https://api.data.gov/signup/
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SCORECARD_BASE_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"

DEFAULT_FIELDS = ",".join([
    "school.name",
    "school.city",
    "school.state",
    "school.school_url",
    "school.ownership",
    "school.locale",
    "latest.admissions.admission_rate.overall",
    "latest.admissions.sat_scores.average.overall",
    "latest.admissions.act_scores.midpoint.cumulative",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.cost.avg_net_price.public",
    "latest.cost.avg_net_price.private",
    "latest.student.size",
    "latest.student.grad_students",
    "latest.completion.rate_suppressed.overall",
    "latest.earnings.10_yrs_after_entry.median",
    "latest.programs.cip_4_digit",
])


async def search_colleges(
    query: str,
    per_page: int = 5,
    extra_filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Search colleges by name or other criteria via the College Scorecard API.

    Args:
        query: School name search string.
        per_page: Number of results to return (max 100).
        extra_filters: Additional API filter parameters, e.g. {"school.state": "CA"}.

    Returns:
        Parsed JSON response from the API.
    """
    params: dict[str, Any] = {
        "api_key": settings.SCORECARD_API_KEY,
        "school.name": query,
        "fields": DEFAULT_FIELDS,
        "_per_page": per_page,
        "_page": 0,
    }
    if extra_filters:
        params.update(extra_filters)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(SCORECARD_BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    logger.debug("Scorecard query=%r returned %d results", query, len(data.get("results", [])))
    return data


async def get_college_by_id(unit_id: int) -> dict[str, Any]:
    """Fetch a single college record by its IPEDS unit ID."""
    params = {
        "api_key": settings.SCORECARD_API_KEY,
        "id": unit_id,
        "fields": DEFAULT_FIELDS,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(SCORECARD_BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()
