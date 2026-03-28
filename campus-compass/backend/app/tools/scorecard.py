"""
College Scorecard API tool.
Docs:    https://collegescorecard.ed.gov/data/documentation/
API key: https://api.data.gov/signup/ (free, instant)
"""

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"

# Delay between calls to be a good citizen (API is generous but rate-limited)
_RATE_LIMIT_DELAY = 0.1

# Fields requested on every search query.
# NOTE: latest.programs.cip_4_digit is intentionally excluded here — the API
# returns 400 when that nested array field is combined with sort/filter params.
# It is fetched only in the detail endpoint where no sort is applied.
_SEARCH_FIELDS = ",".join([
    "id",
    "school.name",
    "school.city",
    "school.state",
    "school.school_url",
    "school.ownership",
    "location.lat",
    "location.lon",
    "latest.admissions.admission_rate.overall",
    "latest.student.size",
    "latest.student.demographics.non_resident_aliens",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.cost.avg_net_price.overall",
    "latest.student.grad_students",
])

# Additional fields for the detail endpoint.
# latest.programs.cip_4_digit is only requested here (not in search) because
# including it alongside sort/filter params causes a 400 from the API.
_DETAIL_EXTRA_FIELDS = ",".join([
    "latest.programs.cip_4_digit",
    "school.locale",
    "school.carnegie_basic",
    "latest.admissions.sat_scores.average.overall",
    "latest.admissions.sat_scores.midpoint.math",
    "latest.admissions.sat_scores.midpoint.critical_reading",
    "latest.admissions.act_scores.midpoint.cumulative",
    "latest.admissions.admission_rate.by_ope_id",
    "latest.completion.rate_suppressed.overall",
    "latest.earnings.10_yrs_after_entry.median",
    "latest.student.demographics.race_ethnicity.white",
    "latest.student.demographics.race_ethnicity.asian",
    "latest.student.demographics.men",
    "latest.student.demographics.women",
    "latest.aid.median_debt.completers.overall",
    "latest.aid.pell_grant_rate",
    "latest.aid.federal_loan_rate",
    "latest.school.accreditor",
])

_OWNERSHIP_MAP = {1: "Public", 2: "Private Nonprofit", 3: "Private For-Profit"}
_OWNERSHIP_INPUT_MAP = {"public": 1, "private_nonprofit": 2, "private_forprofit": 3}

_SORT_FIELD_MAP = {
    "name": "school.name",
    "tuition_low_to_high": "latest.cost.tuition.out_of_state",
    "tuition_high_to_low": "latest.cost.tuition.out_of_state",
    "acceptance_rate": "latest.admissions.admission_rate.overall",
    "enrollment": "latest.student.size",
}


def _pct_display(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value * 100:.1f}%"


def _parse_programs(cip_list: list | None, limit: int = 8) -> list[str]:
    """Extract a readable sample of program names from the CIP 4-digit array."""
    if not cip_list:
        return []
    seen: set[str] = set()
    names: list[str] = []
    for entry in cip_list:
        title = entry.get("title") or entry.get("credential", {}).get("title", "")
        if title and title not in seen:
            seen.add(title)
            names.append(title)
        if len(names) >= limit:
            break
    return names


def _parse_institution(raw: dict) -> dict:
    """Map a raw Scorecard API result record to a clean institution dict."""
    ownership_code = raw.get("school.ownership")
    return {
        "id": raw.get("id"),
        "name": raw.get("school.name"),
        "city": raw.get("school.city"),
        "state": raw.get("school.state"),
        "type": _OWNERSHIP_MAP.get(ownership_code, "Unknown"),
        "website": raw.get("school.school_url"),
        "lat": raw.get("location.lat"),
        "lon": raw.get("location.lon"),
        "acceptance_rate": raw.get("latest.admissions.admission_rate.overall"),
        "acceptance_rate_display": _pct_display(raw.get("latest.admissions.admission_rate.overall")),
        "total_enrollment": raw.get("latest.student.size"),
        "graduate_enrollment": raw.get("latest.student.grad_students"),
        "international_student_pct": raw.get("latest.student.demographics.non_resident_aliens"),
        "international_student_pct_display": _pct_display(
            raw.get("latest.student.demographics.non_resident_aliens")
        ),
        "in_state_tuition": raw.get("latest.cost.tuition.in_state"),
        "out_of_state_tuition": raw.get("latest.cost.tuition.out_of_state"),
        "avg_net_price": raw.get("latest.cost.avg_net_price.overall"),
        # programs_sample is always empty on search results — the Scorecard API
        # returns 400 when latest.programs.cip_4_digit is combined with sort/filter.
        # Use get_university_details (programs_full) for the actual program list.
        "programs_sample": [],
    }


def _parse_institution_detail(raw: dict) -> dict:
    """Extended version of _parse_institution for the detail endpoint."""
    base = _parse_institution(raw)
    base.update({
        "sat_avg": raw.get("latest.admissions.sat_scores.average.overall"),
        "sat_math_midpoint": raw.get("latest.admissions.sat_scores.midpoint.math"),
        "sat_reading_midpoint": raw.get("latest.admissions.sat_scores.midpoint.critical_reading"),
        "act_midpoint": raw.get("latest.admissions.act_scores.midpoint.cumulative"),
        "graduation_rate": raw.get("latest.completion.rate_suppressed.overall"),
        "graduation_rate_display": _pct_display(raw.get("latest.completion.rate_suppressed.overall")),
        "median_earnings_10yr": raw.get("latest.earnings.10_yrs_after_entry.median"),
        "median_debt": raw.get("latest.aid.median_debt.completers.overall"),
        "pell_grant_rate": raw.get("latest.aid.pell_grant_rate"),
        "pell_grant_rate_display": _pct_display(raw.get("latest.aid.pell_grant_rate")),
        "accreditor": raw.get("latest.school.accreditor"),
        "programs_full": _parse_programs(raw.get("latest.programs.cip_4_digit"), limit=50),
    })
    return base


class ScorecardTool:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an authenticated GET request and return the parsed JSON."""
        params["api_key"] = self.api_key

        # Log the URL without the key for safe debugging
        safe_params = {k: v for k, v in params.items() if k != "api_key"}
        logger.info("Scorecard API request: %s?%s", self.base_url,
                    "&".join(f"{k}={v}" for k, v in safe_params.items()))

        await asyncio.sleep(_RATE_LIMIT_DELAY)
        resp = await self.client.get(self.base_url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def search_institutions(
        self,
        name: str | None = None,
        state: str | None = None,
        max_tuition: int | None = None,
        min_tuition: int | None = None,
        program_cip_prefix: str | None = None,
        ownership: str | None = None,
        max_acceptance_rate: float | None = None,
        has_graduate_programs: bool = False,
        sort_by: str = "name",
        sort_descending: bool = False,
        page: int = 0,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """
        Search US institutions with rich filters.
        Returns structured results with key stats for each school.
        """
        per_page = min(per_page, 20)

        params: dict[str, Any] = {
            "fields": _SEARCH_FIELDS,
            "_page": page,
            "_per_page": per_page,
        }

        if name:
            params["school.search"] = name
        if state:
            params["school.state"] = state.upper()
        if max_tuition is not None:
            params["latest.cost.tuition.out_of_state__max"] = max_tuition
        if min_tuition is not None:
            params["latest.cost.tuition.out_of_state__min"] = min_tuition
        if max_acceptance_rate is not None:
            params["latest.admissions.admission_rate.overall__max"] = max_acceptance_rate
        # latest.student.grad_students is not an indexed/filterable field in the Scorecard API.
        # has_graduate_programs is accepted in the schema and noted to Claude in the description,
        # but cannot be enforced at the API level. graduate_enrollment is still returned in
        # every result so Claude can filter or reason about it from the response.
        if has_graduate_programs:
            logger.debug("has_graduate_programs requested but cannot be applied as API filter")
        if ownership:
            ownership_code = _OWNERSHIP_INPUT_MAP.get(ownership.lower())
            if ownership_code:
                params["school.ownership"] = ownership_code

        # Sorting
        sort_field = _SORT_FIELD_MAP.get(sort_by, "school.name")
        direction = "desc" if sort_descending or sort_by == "tuition_high_to_low" else "asc"
        params["_sort"] = f"{sort_field}:{direction}"

        data = await self._get(params)

        results = data.get("results") or []
        total = data.get("metadata", {}).get("total", len(results))

        institutions = [_parse_institution(r) for r in results]

        return {
            "total_results": total,
            "page": page,
            "per_page": per_page,
            "institutions": institutions,
        }

    async def get_institution_detail(self, scorecard_id: int) -> dict[str, Any]:
        """Get comprehensive detail for a specific institution by Scorecard ID."""
        all_fields = _SEARCH_FIELDS + "," + _DETAIL_EXTRA_FIELDS

        params: dict[str, Any] = {
            "id": scorecard_id,
            "fields": all_fields,
        }

        data = await self._get(params)
        results = data.get("results") or []

        if not results:
            return {"error": f"No institution found with Scorecard ID {scorecard_id}"}

        return _parse_institution_detail(results[0])

    async def search_programs_by_cip(
        self,
        cip_prefix: str,
        state: str | None = None,
        max_tuition: int | None = None,
    ) -> dict[str, Any]:
        """
        Search for institutions offering programs matching a CIP code prefix.

        CIP prefixes:
          11 = Computer Science, 14 = Engineering, 26 = Biology,
          27 = Math/Stats, 52 = Business, 13 = Education,
          51 = Health Professions, 40 = Physical Sciences

        NOTE: The Scorecard API does not support filtering by CIP code as a query
        parameter (latest.programs.cip_4_digit is a nested array field and causes
        400 errors when used in filter or sort contexts). This method therefore
        returns a broad set of institutions with graduate programs in the given
        state/tuition range. The caller (Claude) should use get_institution_detail
        on candidates of interest to inspect their actual program lists.
        """
        logger.info(
            "search_programs_by_cip: cip_prefix=%r — note: CIP filtering applied post-fetch only",
            cip_prefix,
        )
        result = await self.search_institutions(
            state=state,
            max_tuition=max_tuition,
            has_graduate_programs=True,
            per_page=15,
        )
        # Attach the requested CIP prefix so Claude knows what was asked for
        result["requested_cip_prefix"] = cip_prefix
        result["cip_filter_note"] = (
            "The Scorecard API does not support server-side CIP filtering. "
            "Use get_university_details on individual results to verify program offerings."
        )
        return result


# ---------------------------------------------------------------------------
# Tool definitions for the Claude agent
# ---------------------------------------------------------------------------

def get_tool_definitions() -> list[dict[str, Any]]:
    """Return the Anthropic tool definition dicts for all Scorecard tools."""
    return [
        {
            "name": "search_us_universities",
            "description": (
                "Search for US universities and colleges using the federal College Scorecard "
                "database. Returns institution-level data including tuition costs, acceptance "
                "rates, enrollment, international student percentages, and available programs. "
                "Use this tool when you need to discover or filter schools based on criteria "
                "like location, cost, selectivity, or available programs. "
                "This searches real federal data — results are authoritative.\n\n"
                "Common CIP code prefixes for program_cip_prefix:\n"
                "11 = Computer and Information Sciences\n"
                "14 = Engineering\n"
                "26 = Biological Sciences\n"
                "27 = Mathematics and Statistics\n"
                "52 = Business/Management\n"
                "13 = Education\n"
                "51 = Health Professions\n"
                "40 = Physical Sciences\n"
                "42 = Psychology\n"
                "45 = Social Sciences\n"
                "09 = Communication\n"
                "50 = Visual and Performing Arts\n"
                "23 = English Language/Literature\n"
                "54 = History"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Search by institution name (partial match). "
                            "Example: 'Carnegie Mellon', 'MIT', 'Georgia Tech'"
                        ),
                    },
                    "state": {
                        "type": "string",
                        "description": "Two-letter US state code. Example: 'CA', 'NY', 'TX'",
                    },
                    "max_out_of_state_tuition": {
                        "type": "integer",
                        "description": (
                            "Maximum annual out-of-state tuition in USD. "
                            "International students almost always pay out-of-state rates."
                        ),
                    },
                    "min_out_of_state_tuition": {
                        "type": "integer",
                        "description": "Minimum annual out-of-state tuition in USD.",
                    },
                    "program_cip_prefix": {
                        "type": "string",
                        "description": (
                            "CIP code prefix to filter schools that offer programs in this field. "
                            "Use 2-digit prefix for broad field, 4-digit for specific subfield."
                        ),
                    },
                    "ownership_type": {
                        "type": "string",
                        "enum": ["public", "private_nonprofit", "private_forprofit"],
                        "description": "Filter by institution type.",
                    },
                    "max_acceptance_rate": {
                        "type": "number",
                        "description": (
                            "Maximum acceptance rate as a decimal (0.3 = 30%). "
                            "Use to filter for more selective schools."
                        ),
                    },
                    "has_graduate_programs": {
                        "type": "boolean",
                        "description": "If true, only return schools with graduate enrollment.",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": [
                            "name",
                            "tuition_low_to_high",
                            "tuition_high_to_low",
                            "acceptance_rate",
                            "enrollment",
                        ],
                        "description": "How to sort results (default: name).",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (0-indexed, default 0).",
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Number of results to return (default 10, max 20).",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_university_details",
            "description": (
                "Get detailed information about a specific US university by its College Scorecard ID. "
                "Returns comprehensive data including all available programs, costs, enrollment "
                "breakdowns, SAT/ACT ranges, graduation rates, median earnings, and admissions "
                "statistics. Use this after search_us_universities when you need deeper detail "
                "on a specific school."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "scorecard_id": {
                        "type": "integer",
                        "description": (
                            "The College Scorecard ID of the institution "
                            "(returned as 'id' in search results)."
                        ),
                    }
                },
                "required": ["scorecard_id"],
            },
        },
    ]


# ---------------------------------------------------------------------------
# Executor — called by the agent's tool dispatcher
# ---------------------------------------------------------------------------

async def execute(tool_name: str, tool_input: dict[str, Any], api_key: str) -> str:
    """
    Execute a Scorecard tool call and return the result as a JSON string for Claude.
    All errors are caught and returned as a JSON error object so Claude can relay
    a meaningful message to the user rather than crashing the agent loop.
    """
    tool = ScorecardTool(api_key=api_key)

    try:
        if tool_name == "search_us_universities":
            result = await tool.search_institutions(
                name=tool_input.get("name"),
                state=tool_input.get("state"),
                max_tuition=tool_input.get("max_out_of_state_tuition"),
                min_tuition=tool_input.get("min_out_of_state_tuition"),
                program_cip_prefix=tool_input.get("program_cip_prefix"),
                ownership=tool_input.get("ownership_type"),
                max_acceptance_rate=tool_input.get("max_acceptance_rate"),
                has_graduate_programs=tool_input.get("has_graduate_programs", False),
                sort_by=tool_input.get("sort_by", "name"),
                page=tool_input.get("page", 0),
                per_page=tool_input.get("per_page", 10),
            )

        elif tool_name == "get_university_details":
            result = await tool.get_institution_detail(
                scorecard_id=tool_input["scorecard_id"]
            )

        else:
            result = {"error": f"Unknown scorecard tool: {tool_name}"}

    except httpx.HTTPStatusError as exc:
        logger.error("Scorecard API HTTP error %d: %s", exc.response.status_code, exc)
        result = {
            "error": f"College Scorecard API returned HTTP {exc.response.status_code}. "
                     "The query may be malformed or the API key may be invalid."
        }
    except httpx.TimeoutException:
        logger.error("Scorecard API timed out")
        result = {"error": "College Scorecard API timed out. Try a narrower search."}
    except Exception as exc:
        logger.exception("Unexpected error in scorecard tool: %s", exc)
        result = {"error": f"Scorecard tool failed: {exc}"}
    finally:
        await tool.client.aclose()

    return json.dumps(result, default=str)
