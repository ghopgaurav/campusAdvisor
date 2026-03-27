"""
General web search tool using the DuckDuckGo Instant Answer / HTML search.
No API key required — uses the DDG HTML endpoint as a lightweight scraper.
Swap this out for Brave Search / Serper / Tavily if you want richer results.
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DDG_URL = "https://html.duckduckgo.com/html/"
MAX_RESULTS = 8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


async def web_search(query: str, max_results: int = MAX_RESULTS) -> list[dict[str, str]]:
    """
    Search the web and return a list of result snippets.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of {"title": str, "url": str, "snippet": str}
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
            resp = await client.post(DDG_URL, data={"q": query, "b": ""})
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        for result in soup.select(".result"):
            title_tag = result.select_one(".result__title a")
            snippet_tag = result.select_one(".result__snippet")

            if not title_tag:
                continue

            title = _clean(title_tag.get_text())
            href = title_tag.get("href", "")
            snippet = _clean(snippet_tag.get_text()) if snippet_tag else ""

            # DDG wraps URLs — extract the real one from the uddg param
            url_match = re.search(r"uddg=([^&]+)", href)
            if url_match:
                from urllib.parse import unquote
                href = unquote(url_match.group(1))

            if title and href:
                results.append({"title": title, "url": href, "snippet": snippet})

            if len(results) >= max_results:
                break

        logger.debug("web_search(%r) -> %d results", query, len(results))
        return results

    except Exception as exc:
        logger.warning("web_search failed for %r: %s", query, exc)
        return []
