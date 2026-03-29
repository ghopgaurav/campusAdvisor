"""
Tool registry — defines all tools available to the Claude agent.
Each entry is an Anthropic tool definition dict plus a corresponding async handler.
"""

import json
import logging
from typing import Any

from app.config import settings
from app.tools.cost_of_living import execute as col_execute, get_tool_definition as col_tool_def
from app.tools.page_fetcher import execute as page_fetcher_execute, get_tool_definition as page_fetcher_tool_def
from app.tools.reddit_search import execute as reddit_execute, get_tool_definition as reddit_tool_def
from app.tools.scorecard import execute as scorecard_execute, get_tool_definitions as scorecard_tool_defs
from app.tools.web_search import execute as web_search_execute, get_tool_definition as web_search_tool_def

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Aggregate tool definitions from all tool modules
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    # --- Scorecard: search_us_universities + get_university_details ---
    *scorecard_tool_defs(),

    # --- Page fetcher: fetch_university_page ---
    page_fetcher_tool_def(),

    # --- Web search ---
    web_search_tool_def(),

    # --- Cost of living ---
    col_tool_def(),

    # --- Reddit / student discussions ---
    reddit_tool_def(),
]

# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

_SCORECARD_TOOLS = {"search_us_universities", "get_university_details"}
_PAGE_FETCHER_TOOLS = {"fetch_university_page"}
_WEB_SEARCH_TOOLS = {"web_search"}


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

    if tool_name in _PAGE_FETCHER_TOOLS:
        return await page_fetcher_execute(
            tool_name=tool_name,
            tool_input=tool_input,
            config=settings,
        )

    if tool_name in _WEB_SEARCH_TOOLS:
        return await web_search_execute(tool_name=tool_name, tool_input=tool_input)

    if tool_name == "get_living_costs":
        return await col_execute(tool_name=tool_name, tool_input=tool_input)

    if tool_name == "search_student_discussions":
        return await reddit_execute(tool_name=tool_name, tool_input=tool_input)

    logger.warning("Unknown tool requested: %s", tool_name)
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
