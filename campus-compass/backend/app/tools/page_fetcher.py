"""
University page fetcher and text extractor.
Uses readability-lxml to strip boilerplate and return clean article text.
"""

import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from readability import Document

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 12_000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CampusCompassBot/1.0; "
        "+https://github.com/ghopgaurav/campusAdvisor)"
    )
}


def _is_allowed_domain(url: str) -> bool:
    """Basic safety check — only fetch http/https URLs."""
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https")


def _extract_text(html: str, url: str) -> str:
    """Extract main readable text from raw HTML using readability + BS4 fallback."""
    try:
        doc = Document(html)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "lxml")
        text = soup.get_text(separator="\n", strip=True)
        if len(text) > 200:
            return text[:MAX_CONTENT_CHARS]
    except Exception as exc:
        logger.debug("readability failed for %s: %s", url, exc)

    # Fallback: raw BS4 body text
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)[:MAX_CONTENT_CHARS]


async def fetch_page(url: str) -> dict[str, str]:
    """
    Fetch a URL and return extracted readable text.

    Returns:
        {
            "url": str,
            "title": str,
            "content": str,   # truncated to MAX_CONTENT_CHARS
            "error": str | None,
        }
    """
    if not _is_allowed_domain(url):
        return {"url": url, "title": "", "content": "", "error": "Disallowed URL scheme"}

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers=HEADERS,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        doc = Document(html)
        title = doc.title() or ""
        content = _extract_text(html, url)
        logger.debug("Fetched %s (%d chars)", url, len(content))
        return {"url": url, "title": title, "content": content, "error": None}

    except httpx.HTTPStatusError as exc:
        logger.warning("HTTP %d fetching %s", exc.response.status_code, url)
        return {"url": url, "title": "", "content": "", "error": f"HTTP {exc.response.status_code}"}
    except Exception as exc:
        logger.warning("Error fetching %s: %s", url, exc)
        return {"url": url, "title": "", "content": "", "error": str(exc)}
