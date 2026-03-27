"""
Tool registry — defines all tools available to the Claude agent.
Each entry is an Anthropic tool definition dict plus a corresponding async handler.
"""

import json
import logging
from typing import Any

from app.config import settings
from app.tools.cost_of_living import get_cost_of_living
from app.tools.page_fetcher import fetch_page
from app.tools.reddit_search import reddit_search
from app.tools.scorecard import execute as scorecard_execute, get_tool_definitions as scorecard_tool_defs
from app.tools.web_search import web_search

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Aggregate tool definitions from all tool modules
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    # --- Scorecard: search_us_universities + get_university_details ---
    *scorecard_tool_defs(),

    # --- Page fetcher ---
    {
        "name": "fetch_page",
        "description": (
            "Fetch and extract the main text content from a URL. Use this to read program pages, "
            "admissions requirements, deadlines, faculty profiles, and other university web pages. "
            "Returns the title and readable body text of the page."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the page to fetch (must be http or https).",
                },
            },
            "required": ["url"],
        },
    },

    # --- Web search ---
    {
        "name": "web_search",
        "description": (
            "Search the web for current information about universities, programs, rankings, "
            "news, and anything else. Use this when you need up-to-date or time-sensitive "
            "information that may not be in your training data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (be specific for better results).",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 6).",
                    "default": 6,
                },
            },
            "required": ["query"],
        },
    },

    # --- Cost of living ---
    {
        "name": "cost_of_living",
        "description": (
            "Look up cost-of-living data for a city: rent, food, transport, and utilities. "
            "Use this whenever discussing whether a student can afford to live somewhere, "
            "or when comparing stipends/salaries against local living costs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name (e.g. 'Boston', 'San Francisco').",
                },
                "country": {
                    "type": "string",
                    "description": "Country name (default 'United States').",
                    "default": "United States",
                },
            },
            "required": ["city"],
        },
    },

    # --- Reddit search ---
    {
        "name": "reddit_search",
        "description": (
            "Search Reddit and graduate school forums for real student experiences, opinions, "
            "and discussions about programs, universities, and the application process. "
            "Best for 'what's it actually like' questions, acceptance data points, and "
            "community sentiment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. 'MIT CS PhD acceptance rate 2024').",
                },
                "subreddits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Subreddits to search. Defaults to grad school subs. "
                        "Options: gradadmissions, GradSchool, ApplyingToCollege, MBA, PhD, cscareerquestions."
                    ),
                },
                "sort": {
                    "type": "string",
                    "enum": ["relevance", "top", "new", "comments"],
                    "description": "Sort order (default: relevance).",
                    "default": "relevance",
                },
                "time_filter": {
                    "type": "string",
                    "enum": ["week", "month", "year", "all"],
                    "description": "Time range filter (default: year).",
                    "default": "year",
                },
            },
            "required": ["query"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

_SCORECARD_TOOLS = {"search_us_universities", "get_university_details"}


async def dispatch_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """
    Execute a tool by name and return its result as a JSON string.
    All tool calls are async HTTP requests.
    """
    logger.info("Dispatching tool: %s | input: %s", tool_name, tool_input)

    if tool_name in _SCORECARD_TOOLS:
        return await scorecard_execute(
            tool_name=tool_name,
            tool_input=tool_input,
            api_key=settings.require_scorecard_key(),
        )

    if tool_name == "fetch_page":
        result = await fetch_page(url=tool_input["url"])
        return json.dumps(result, default=str)

    if tool_name == "web_search":
        result = await web_search(
            query=tool_input["query"],
            max_results=tool_input.get("max_results", 6),
        )
        return json.dumps(result, default=str)

    if tool_name == "cost_of_living":
        result = await get_cost_of_living(
            city=tool_input["city"],
            country=tool_input.get("country", "United States"),
        )
        return json.dumps(result, default=str)

    if tool_name == "reddit_search":
        result = await reddit_search(
            query=tool_input["query"],
            subreddits=tool_input.get("subreddits"),
            sort=tool_input.get("sort", "relevance"),
            time_filter=tool_input.get("time_filter", "year"),
        )
        return json.dumps(result, default=str)

    logger.warning("Unknown tool requested: %s", tool_name)
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
