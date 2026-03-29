"""
Reddit community search tool.

Searches Reddit via DuckDuckGo's site: filter — no Reddit OAuth or API key needed.
Results are always tagged with a disclaimer that they are anecdotal/community data.
"""

import asyncio
import json
import logging
import re
from typing import Any

from ddgs import DDGS

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "These are community opinions and personal experiences — not official or verified "
    "information. Individual experiences may vary significantly."
)

# Subreddits most relevant to international grad students
_RELEVANT_SUBREDDITS = [
    "gradadmissions",
    "MSCS",
    "GradSchool",
    "IntlStudents",
    "ApplyingToCollege",
    "csMajors",
    "MBA",
    "immigration",
    "f1visa",
]

# Delay to avoid DDG rate-limiting (shared with web_search)
_SEARCH_DELAY = 1.0

_REDDIT_URL_RE = re.compile(r"reddit\.com/r/(\w+)/", re.IGNORECASE)


def _extract_subreddit(url: str) -> str | None:
    """Parse the subreddit name out of a Reddit URL."""
    m = _REDDIT_URL_RE.search(url)
    return m.group(1) if m else None


def _run_ddg_search(query: str, max_results: int) -> list[dict[str, str]]:
    """Synchronous DDG text search — called via asyncio.to_thread."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
    return results


class RedditSearchTool:

    def __init__(self) -> None:
        self.relevant_subreddits = _RELEVANT_SUBREDDITS

    async def search_reddit(
        self,
        query: str,
        subreddit: str | None = None,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """
        Search Reddit for student experiences and discussions.
        Uses DuckDuckGo with site:reddit.com filter — no OAuth needed.

        Returns structured results always including the community disclaimer.
        """
        max_results = min(max_results, 8)

        # Build the site-restricted DDG query
        if subreddit:
            ddg_query = f"site:reddit.com/r/{subreddit} {query}"
        else:
            # Target the most relevant subreddits with an OR filter
            sub_filter = " OR ".join(
                f"r/{s}" for s in self.relevant_subreddits
            )
            ddg_query = f"site:reddit.com ({sub_filter}) {query}"

        logger.info("reddit_search: ddg_query=%r max=%d", ddg_query, max_results)

        await asyncio.sleep(_SEARCH_DELAY)

        try:
            raw_results = await asyncio.to_thread(_run_ddg_search, ddg_query, max_results)
        except Exception as exc:
            logger.warning("DDG reddit search failed (%r): %s — trying simple fallback", ddg_query, exc)
            # Fallback: plain site:reddit.com without subreddit filter
            fallback_query = f"site:reddit.com {query}"
            try:
                await asyncio.sleep(_SEARCH_DELAY)
                raw_results = await asyncio.to_thread(_run_ddg_search, fallback_query, max_results)
            except Exception as exc2:
                logger.error("Reddit search fallback also failed: %s", exc2)
                return {
                    "query": query,
                    "source": "Reddit (community discussions)",
                    "disclaimer": _DISCLAIMER,
                    "results": [],
                    "total_results": 0,
                    "error": f"Search failed: {exc2}",
                }

        # Filter to only Reddit URLs and enrich with subreddit name
        results = []
        for r in raw_results:
            url = r.get("url", "")
            if "reddit.com" not in url:
                continue
            results.append({
                "title": r["title"],
                "url": url,
                "subreddit": _extract_subreddit(url),
                "snippet": r["snippet"],
            })

        # If the subreddit filter was too aggressive and returned nothing, retry simply
        if not results and subreddit is None:
            logger.info("Subreddit-filtered search returned 0 Reddit URLs, retrying simply")
            try:
                await asyncio.sleep(_SEARCH_DELAY)
                fallback_results = await asyncio.to_thread(
                    _run_ddg_search, f"site:reddit.com {query}", max_results
                )
                for r in fallback_results:
                    url = r.get("url", "")
                    if "reddit.com" not in url:
                        continue
                    results.append({
                        "title": r["title"],
                        "url": url,
                        "subreddit": _extract_subreddit(url),
                        "snippet": r["snippet"],
                    })
            except Exception as exc3:
                logger.warning("Simple reddit fallback failed: %s", exc3)

        logger.info("reddit_search(%r) -> %d results", query, len(results))

        return {
            "query": query,
            "source": "Reddit (community discussions)",
            "disclaimer": _DISCLAIMER,
            "results": results,
            "total_results": len(results),
        }


# ---------------------------------------------------------------------------
# Tool definition for Claude
# ---------------------------------------------------------------------------

def get_tool_definition() -> dict[str, Any]:
    sub_list = ", ".join(_RELEVANT_SUBREDDITS)
    return {
        "name": "search_student_discussions",
        "description": (
            "Search Reddit and student communities for real experiences, opinions, and "
            "practical advice about US universities, programs, campus life, and cities. "
            "Returns community discussions — these are personal opinions and anecdotal "
            "experiences, NOT official data.\n\n"
            "Good uses:\n"
            "- 'What is student life like at CMU?'\n"
            "- 'How hard is it to get an assistantship at Georgia Tech?'\n"
            "- 'Is X city safe for international students?'\n"
            "- 'How are job prospects after MS CS from X university?'\n"
            "- 'What do current students think of X program?'\n\n"
            "ALWAYS present these results as community opinions, clearly separate from "
            "official data.\n\n"
            f"Default subreddits searched: {sub_list}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query about student experiences. "
                        "Be specific about the school, program, or topic."
                    ),
                },
                "subreddit": {
                    "type": "string",
                    "description": (
                        f"Optional: specific subreddit to search. Options: {sub_list}"
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (default 5, max 8).",
                },
            },
            "required": ["query"],
        },
    }


# ---------------------------------------------------------------------------
# Executor — called by the agent's tool dispatcher
# ---------------------------------------------------------------------------

async def execute(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Execute search_student_discussions and return JSON string for Claude."""
    tool = RedditSearchTool()
    try:
        result = await tool.search_reddit(
            query=tool_input["query"],
            subreddit=tool_input.get("subreddit"),
            max_results=tool_input.get("max_results", 5),
        )
    except Exception as exc:
        logger.exception("Unexpected error in reddit_search execute: %s", exc)
        result = {
            "query": tool_input.get("query", ""),
            "source": "Reddit (community discussions)",
            "disclaimer": _DISCLAIMER,
            "results": [],
            "total_results": 0,
            "error": f"Reddit search tool failed: {exc}",
        }
    return json.dumps(result, default=str)
