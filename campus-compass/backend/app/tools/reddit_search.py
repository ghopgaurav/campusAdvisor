"""
Reddit search tool.
Uses Reddit's public JSON search endpoint (no OAuth required for read-only search).
Targets graduate school / college admission subreddits by default.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"

DEFAULT_SUBREDDITS = [
    "gradadmissions",
    "GradSchool",
    "ApplyingToCollege",
    "MBA",
    "cscareerquestions",
    "PhD",
]

HEADERS = {
    "User-Agent": "CampusCompassBot/1.0 (educational research tool)",
}

MAX_POSTS = 8


async def reddit_search(
    query: str,
    subreddits: list[str] | None = None,
    limit: int = MAX_POSTS,
    sort: str = "relevance",
    time_filter: str = "year",
) -> list[dict[str, Any]]:
    """
    Search Reddit for posts matching a query.

    Args:
        query: Search query string.
        subreddits: List of subreddits to restrict search to. Defaults to grad school subs.
        limit: Max posts to return (Reddit caps at 100).
        sort: "relevance" | "top" | "new" | "comments"
        time_filter: "hour" | "day" | "week" | "month" | "year" | "all"

    Returns:
        List of post dicts with keys: title, url, subreddit, score, num_comments, selftext_preview.
    """
    subs = subreddits or DEFAULT_SUBREDDITS
    restrict_sr = "+".join(subs)

    params = {
        "q": query,
        "restrict_sr": restrict_sr,
        "sort": sort,
        "t": time_filter,
        "limit": limit,
        "type": "link",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
            resp = await client.get(
                f"https://www.reddit.com/r/{restrict_sr}/search.json",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            selftext = post.get("selftext", "")
            posts.append({
                "title": post.get("title", ""),
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "subreddit": post.get("subreddit", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "selftext_preview": selftext[:500] if selftext else "",
                "created_utc": post.get("created_utc"),
            })

        logger.debug("reddit_search(%r) -> %d posts", query, len(posts))
        return posts

    except Exception as exc:
        logger.warning("reddit_search failed for %r: %s", query, exc)
        return []
