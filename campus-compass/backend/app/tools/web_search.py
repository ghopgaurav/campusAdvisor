"""
General web search tool using the DuckDuckGo Search Python library.
No API key required. Uses DDGS (sync) run in a thread executor so it plays
nicely with the async agent loop without blocking the event loop.
"""

import asyncio
import json
import logging
import re
from typing import Any

from ddgs import DDGS

logger = logging.getLogger(__name__)

# Polite delay between consecutive searches to avoid DDG rate-limiting
_SEARCH_DELAY = 1.0

# Keywords that suggest the query is better served by DDG news search.
# Years alone are intentionally excluded — "CMU MSCS 2025" is an admissions
# query, not a news query. Only explicit news-intent words trigger news mode.
_NEWS_KEYWORDS = re.compile(
    r"\b(news|latest|recent|today|this week|announced|breaking|just announced|new policy)\b",
    re.IGNORECASE,
)


def _is_news_query(query: str) -> bool:
    return bool(_NEWS_KEYWORDS.search(query))


def _run_text_search(query: str, max_results: int, region: str) -> list[dict[str, str]]:
    """Synchronous DDG text search — called via asyncio.to_thread."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region=region, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
    return results


def _run_news_search(query: str, max_results: int, region: str) -> list[dict[str, str]]:
    """Synchronous DDG news search — called via asyncio.to_thread."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.news(query, region=region, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("body", ""),
                "date": r.get("date", ""),
                "source": r.get("source", ""),
            })
    return results


class WebSearchTool:

    async def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "us-en",
    ) -> dict[str, Any]:
        """
        Search the web for current information.

        Automatically uses the DDG news endpoint for time-sensitive queries
        (detected via keywords like "latest", "2025", "news", etc.).
        Runs the synchronous DDGS client in a thread so the event loop
        is never blocked.

        Returns:
        {
            "query": str,
            "results": [{"title", "url", "snippet", ...}],
            "total_results": int,
            "search_type": "text" | "news",
            "search_engine": "DuckDuckGo"
        }
        """
        max_results = min(max_results, 10)
        use_news = _is_news_query(query)
        search_type = "news" if use_news else "text"

        logger.info("web_search: query=%r type=%s max=%d", query, search_type, max_results)

        await asyncio.sleep(_SEARCH_DELAY)

        try:
            if use_news:
                results = await asyncio.to_thread(
                    _run_news_search, query, max_results, region
                )
            else:
                results = await asyncio.to_thread(
                    _run_text_search, query, max_results, region
                )
        except Exception as exc:
            logger.warning("DDG %s search failed for %r: %s", search_type, query, exc)
            results = []

        # If primary returned nothing, try the other search type before giving up
        if not results:
            fallback_type = "text" if use_news else "news"
            logger.info("Primary returned 0 results, retrying %r with %s search", query, fallback_type)
            try:
                await asyncio.sleep(_SEARCH_DELAY)
                if use_news:
                    results = await asyncio.to_thread(_run_text_search, query, max_results, region)
                else:
                    results = await asyncio.to_thread(_run_news_search, query, max_results, region)
                if results:
                    search_type = fallback_type
            except Exception as exc2:
                logger.error("DDG fallback also failed for %r: %s", query, exc2)
                return {
                    "query": query,
                    "results": [],
                    "total_results": 0,
                    "search_type": search_type,
                    "search_engine": "DuckDuckGo",
                    "error": f"Search failed: {exc2}",
                }

        logger.info("web_search(%r) -> %d results", query, len(results))
        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "search_type": search_type,
            "search_engine": "DuckDuckGo",
        }


# ---------------------------------------------------------------------------
# Tool definition for Claude
# ---------------------------------------------------------------------------

def get_tool_definition() -> dict[str, Any]:
    return {
        "name": "web_search",
        "description": (
            "Search the web for current information about US universities, admissions, "
            "visa policies, city conditions, student experiences, or any other topic. "
            "Use this when you need up-to-date information that isn't available through "
            "the College Scorecard database.\n\n"
            "Good uses:\n"
            "- Finding specific program deadlines or requirements\n"
            "- Current visa/immigration policy information\n"
            "- Recent university news or changes\n"
            "- City-specific information (safety, housing, transport)\n"
            "- Finding official university page URLs to then fetch with fetch_university_page\n\n"
            "Tips:\n"
            "- Be specific in queries: 'CMU MSCS GRE requirement 2025' not 'computer science GRE'\n"
            "- Include the year for time-sensitive info\n"
            "- For visa/immigration, search official sources: 'USCIS F-1 student work authorization'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific and include relevant context.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 10).",
                },
            },
            "required": ["query"],
        },
    }


# ---------------------------------------------------------------------------
# Executor — called by the agent's tool dispatcher
# ---------------------------------------------------------------------------

async def execute(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Execute web_search and return JSON string for Claude."""
    tool = WebSearchTool()
    try:
        result = await tool.search(
            query=tool_input["query"],
            max_results=tool_input.get("max_results", 5),
        )
    except Exception as exc:
        logger.exception("Unexpected error in web_search execute: %s", exc)
        result = {
            "query": tool_input.get("query", ""),
            "results": [],
            "total_results": 0,
            "error": f"Search tool failed: {exc}",
        }
    return json.dumps(result, default=str)
