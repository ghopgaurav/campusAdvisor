"""
University page fetcher and structured extractor.

Fetches a university webpage, cleans the HTML into readable markdown-like text,
then calls Claude Haiku to extract structured JSON based on the extraction_focus.
This is intentionally a "nested LLM call" — cheap + fast Haiku does the extraction
so the main agent (Sonnet) doesn't have to process raw HTML.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from anthropic import AsyncAnthropicBedrock
import httpx
from bs4 import BeautifulSoup, Tag
from readability import Document

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 6000

# ---------------------------------------------------------------------------
# Extraction prompts — one per focus type
# ---------------------------------------------------------------------------

EXTRACTION_PROMPTS: dict[str, str] = {
    "admissions": """Extract admissions information from this university web page.
Return ONLY a JSON object with these fields (null if not found, do NOT guess):
{
    "gre_required": "required" | "optional" | "not_required" | null,
    "gre_quantitative_avg": integer or null,
    "gre_verbal_avg": integer or null,
    "gmat_required": "required" | "optional" | "not_required" | null,
    "gmat_avg": integer or null,
    "toefl_minimum": integer or null,
    "ielts_minimum": float or null,
    "duolingo_minimum": integer or null,
    "minimum_gpa": float or null,
    "average_admitted_gpa": float or null,
    "application_deadline_fall": "string" or null,
    "application_deadline_spring": "string" or null,
    "application_fee": integer in USD or null,
    "required_materials": "string" or null,
    "important_notes": "string" or null
}""",

    "tuition": """Extract tuition and cost information from this university web page.
Return ONLY a JSON object with these fields (null if not found, do NOT guess):
{
    "tuition_per_credit": integer in USD or null,
    "tuition_per_semester": integer in USD or null,
    "tuition_per_year": integer in USD or null,
    "total_program_cost": integer in USD or null,
    "fees_per_semester": integer in USD or null,
    "international_student_fee": integer in USD or null,
    "health_insurance_cost": integer in USD or null,
    "estimated_total_cost_of_attendance": integer in USD or null,
    "financial_aid_available": true | false | null,
    "merit_scholarships": "string description" or null,
    "important_notes": "string" or null
}""",

    "program": """Extract program/curriculum information from this university web page.
Return ONLY a JSON object with these fields (null if not found, do NOT guess):
{
    "program_name": "string" or null,
    "degree_type": "string" or null,
    "department": "string" or null,
    "total_credits": integer or null,
    "duration": "string" or null,
    "thesis_option": true | false | null,
    "non_thesis_option": true | false | null,
    "core_courses": ["list of course names"] or null,
    "specializations": ["list of specialization/track names"] or null,
    "stem_designated": true | false | null,
    "prerequisites": "string" or null,
    "capstone_or_project": true | false | null,
    "important_notes": "string" or null
}""",

    "funding": """Extract funding and financial support information from this university web page.
Return ONLY a JSON object with these fields (null if not found, do NOT guess):
{
    "teaching_assistantships": true | false | null,
    "research_assistantships": true | false | null,
    "assistantship_stipend": "string" or null,
    "tuition_waiver_with_assistantship": true | false | null,
    "fellowships": "string description" or null,
    "scholarships": "string description" or null,
    "how_to_apply_for_funding": "string" or null,
    "funding_deadline": "string" or null,
    "percentage_students_funded": "string" or null,
    "important_notes": "string" or null
}""",

    "international": """Extract information relevant to international students from this university web page.
Return ONLY a JSON object with these fields (null if not found, do NOT guess):
{
    "international_admissions_url": "string" or null,
    "international_student_office": "string" or null,
    "visa_support": "string" or null,
    "i20_process_notes": "string" or null,
    "english_proficiency_requirements": "string" or null,
    "credential_evaluation_required": true | false | null,
    "credential_evaluation_service": "string" or null,
    "international_student_orientation": "string" or null,
    "on_campus_employment": "string" or null,
    "cpt_opt_information": "string" or null,
    "important_notes": "string" or null
}""",

    "general": """Extract the most important information from this university web page.
Return ONLY a JSON object summarizing the key facts found on this page. Include fields like
program details, requirements, costs, deadlines, or any other relevant information.
Use null for anything not found. Do NOT guess or infer.""",
}


# ---------------------------------------------------------------------------
# HTML → structured text conversion
# ---------------------------------------------------------------------------

def _tag_to_markdown(tag: Tag, base_url: str = "") -> str:
    """Recursively convert a BS4 tag to markdown-like plain text."""
    parts: list[str] = []

    for child in tag.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                parts.append(text)
            continue

        if not isinstance(child, Tag):
            continue

        name = child.name.lower() if child.name else ""

        if name in ("script", "style", "nav", "footer", "header",
                    "aside", "noscript", "form", "button", "svg"):
            continue

        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(name[1])
            inner = child.get_text(strip=True)
            if inner:
                parts.append(f"\n{'#' * level} {inner}\n")

        elif name in ("p", "div", "section", "article"):
            inner = _tag_to_markdown(child, base_url)
            if inner.strip():
                parts.append(f"\n{inner.strip()}\n")

        elif name in ("ul", "ol"):
            for li in child.find_all("li", recursive=False):
                item = li.get_text(" ", strip=True)
                if item:
                    parts.append(f"- {item}")
            parts.append("")

        elif name == "table":
            rows = child.find_all("tr")
            table_lines: list[str] = []
            for i, row in enumerate(rows):
                cells = [td.get_text(" ", strip=True) for td in row.find_all(["td", "th"])]
                table_lines.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    table_lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
            parts.append("\n" + "\n".join(table_lines) + "\n")

        elif name == "a":
            href = child.get("href", "")
            text = child.get_text(strip=True)
            if href and text:
                # Keep absolute URLs and relevant relative ones
                if href.startswith("http") or href.startswith("/"):
                    parts.append(f"{text} ({href})")
                else:
                    parts.append(text)
            elif text:
                parts.append(text)

        elif name in ("strong", "b", "em", "i", "span", "label"):
            inner = child.get_text(" ", strip=True)
            if inner:
                parts.append(inner)

        elif name == "br":
            parts.append("\n")

        elif name in ("li", "td", "th", "caption", "figcaption"):
            inner = child.get_text(" ", strip=True)
            if inner:
                parts.append(inner)

        else:
            inner = _tag_to_markdown(child, base_url)
            if inner.strip():
                parts.append(inner.strip())

    return " ".join(parts)


def _clean_html_to_text(html: str, url: str) -> tuple[str, str]:
    """
    Convert raw HTML to clean structured text.
    Returns (title, cleaned_text).

    Strategy:
    1. Try readability-lxml first — best for article-style pages
    2. Fall back to targeted BS4 extraction for structured pages (tables, forms)
    3. Normalize whitespace and truncate
    """
    title = ""

    # --- Primary: readability ---
    try:
        doc = Document(html)
        title = doc.title() or ""
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "lxml")
        text = _tag_to_markdown(soup, url)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) > 300:
            return title, text[:_MAX_CONTENT_CHARS]
    except Exception as exc:
        logger.debug("readability failed for %s: %s", url, exc)

    # --- Fallback: manual BS4 extraction ---
    soup = BeautifulSoup(html, "lxml")

    # Extract title from <title> tag if readability didn't give us one
    if not title and soup.title:
        title = soup.title.get_text(strip=True)

    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "noscript", "form", "button", "svg", "iframe"]):
        tag.decompose()

    # Find the main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find(id=re.compile(r"main|content|body", re.I))
        or soup.find(class_=re.compile(r"main|content|body", re.I))
        or soup.find("body")
    )

    if not main:
        main = soup

    text = _tag_to_markdown(main, url)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, text[:_MAX_CONTENT_CHARS]


# ---------------------------------------------------------------------------
# PageFetcherTool class
# ---------------------------------------------------------------------------

class PageFetcherTool:
    def __init__(self, config) -> None:
        access_key, secret_key = config.require_aws_credentials()
        self.http_client = httpx.AsyncClient(
            timeout=20.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CampusCompass/1.0; educational research bot)",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
        )
        self.anthropic_client = AsyncAnthropicBedrock(
            aws_access_key=access_key,
            aws_secret_key=secret_key,
            aws_region=config.AWS_REGION,
        )
        self._extraction_model = config.ANTHROPIC_MODEL_CHEAP

    async def fetch_and_extract(
        self,
        url: str,
        extraction_focus: str = "general",
    ) -> dict[str, Any]:
        """
        Fetch a university web page and extract structured information via Claude Haiku.

        extraction_focus: "admissions" | "tuition" | "program" | "funding" |
                          "international" | "general"
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return _error_result(url, extraction_focus, "Invalid URL scheme — only http/https allowed")

        # ── Step 1: Fetch ──────────────────────────────────────────────────
        try:
            resp = await self.http_client.get(url)
        except httpx.TimeoutException:
            return _error_result(url, extraction_focus,
                                 f"Request timed out fetching {url}. The server may be slow.")
        except httpx.ConnectError:
            return _error_result(url, extraction_focus,
                                 f"Could not connect to {url}. Check the URL or try later.")
        except httpx.SSLError:
            return _error_result(url, extraction_focus,
                                 f"SSL certificate error for {url}.")
        except Exception as exc:
            return _error_result(url, extraction_focus, f"Fetch failed: {exc}")

        if resp.status_code == 404:
            return _error_result(url, extraction_focus,
                                 "Page not found (404). The URL may be outdated or incorrect.")
        if resp.status_code == 403:
            return _error_result(url, extraction_focus,
                                 "Access denied (403). This page blocks automated access.")
        if resp.status_code != 200:
            return _error_result(url, extraction_focus,
                                 f"HTTP {resp.status_code} from {url}.")

        html = resp.text

        # ── Step 2: Clean HTML → structured text ──────────────────────────
        page_title, cleaned_text = _clean_html_to_text(html, url)

        if len(cleaned_text.strip()) < 50:
            return _error_result(url, extraction_focus,
                                 "Page returned too little readable content. "
                                 "It may require JavaScript or login.")

        logger.info("Fetched %s (%d chars cleaned) — focus: %s", url, len(cleaned_text), extraction_focus)

        # ── Step 3: LLM extraction ─────────────────────────────────────────
        extraction_prompt = EXTRACTION_PROMPTS.get(extraction_focus, EXTRACTION_PROMPTS["general"])

        system = (
            "You are a precise data extraction assistant. "
            "You extract structured information from university web pages. "
            "Return ONLY valid JSON — no markdown fences, no explanation, no preamble."
        )

        user_message = (
            f"{extraction_prompt}\n\n"
            f"--- PAGE CONTENT FROM: {url} ---\n\n"
            f"{cleaned_text}"
        )

        try:
            llm_resp = await self.anthropic_client.messages.create(
                model=self._extraction_model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            raw_output = llm_resp.content[0].text.strip()
        except Exception as exc:
            logger.error("LLM extraction failed for %s: %s", url, exc)
            return _error_result(url, extraction_focus,
                                 f"AI extraction step failed: {exc}")

        # ── Step 4: Parse JSON and return ──────────────────────────────────
        extracted_data, parse_error = _parse_json(raw_output)

        return {
            "url": url,
            "page_title": page_title,
            "extraction_focus": extraction_focus,
            "extracted_data": extracted_data,
            "raw_extraction": raw_output if parse_error else None,
            "parse_error": parse_error,
            "page_text_preview": cleaned_text[:500],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "success": parse_error is None,
        }

    async def aclose(self) -> None:
        await self.http_client.aclose()
        await self.anthropic_client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_result(url: str, focus: str, message: str) -> dict[str, Any]:
    return {
        "url": url,
        "page_title": None,
        "extraction_focus": focus,
        "extracted_data": None,
        "raw_extraction": None,
        "parse_error": None,
        "page_text_preview": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "success": False,
        "error": message,
    }


def _parse_json(raw: str) -> tuple[Any, str | None]:
    """
    Parse JSON from LLM output.
    Strips markdown fences if present, returns (parsed, error_message).
    """
    # Strip ```json ... ``` fences if model ignored the instruction
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed: %s | raw: %.200s", exc, raw)
        return None, f"JSON parse error: {exc}"


# ---------------------------------------------------------------------------
# Tool definition for Claude
# ---------------------------------------------------------------------------

def get_tool_definition() -> dict[str, Any]:
    return {
        "name": "fetch_university_page",
        "description": (
            "Fetch a specific university web page and extract structured information from it. "
            "Use this when you have a specific URL for a program page, admissions page, "
            "tuition page, or scholarship page and need to extract detailed requirements, "
            "costs, or program information.\n\n"
            "IMPORTANT: Only use this for .edu URLs or known university domains. "
            "This tool makes a real HTTP request and uses AI extraction, so use it "
            "selectively — prefer search_us_universities for basic institutional data.\n\n"
            "Tips for finding URLs:\n"
            "- Most program pages follow patterns like: university.edu/graduate/programs/computer-science\n"
            "- Admissions pages: university.edu/admissions or university.edu/graduate-admissions\n"
            "- You can also get URLs from search_us_universities results (the website field)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the university web page to fetch",
                },
                "extraction_focus": {
                    "type": "string",
                    "enum": ["admissions", "tuition", "program", "funding", "international", "general"],
                    "description": (
                        "What type of information to focus on extracting:\n"
                        "- admissions: requirements, deadlines, test scores, GPA\n"
                        "- tuition: costs, fees, financial aid, scholarships\n"
                        "- program: curriculum, courses, thesis options, duration, credits\n"
                        "- funding: assistantships, fellowships, scholarships\n"
                        "- international: visa, I-20, English requirements, CPT/OPT\n"
                        "- general: extract whatever seems most relevant"
                    ),
                },
            },
            "required": ["url"],
        },
    }


# ---------------------------------------------------------------------------
# Executor — called by the agent's tool dispatcher
# ---------------------------------------------------------------------------

async def execute(tool_name: str, tool_input: dict[str, Any], config) -> str:
    """
    Execute the fetch_university_page tool and return a JSON string for Claude.
    Errors are returned as JSON so the agent can communicate them to the user.
    """
    tool = PageFetcherTool(config=config)
    try:
        result = await tool.fetch_and_extract(
            url=tool_input["url"],
            extraction_focus=tool_input.get("extraction_focus", "general"),
        )
    except Exception as exc:
        logger.exception("Unexpected error in page_fetcher execute: %s", exc)
        result = _error_result(
            url=tool_input.get("url", "unknown"),
            focus=tool_input.get("extraction_focus", "general"),
            message=f"Unexpected tool error: {exc}",
        )
    finally:
        await tool.aclose()

    return json.dumps(result, default=str)
