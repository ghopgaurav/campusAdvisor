"""
Smoke test for the PageFetcherTool.
Run from backend/: python test_page_fetcher.py

Reads ANTHROPIC_API_KEY from .env automatically.
Requires network access to fetch live university pages.
"""

import asyncio
import json
import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not API_KEY or API_KEY == "your_key_here":
    raise SystemExit(
        "\n❌  ANTHROPIC_API_KEY is not set.\n"
        "    Add it to backend/.env and rerun.\n"
    )


async def test_admissions(tool) -> None:
    print("\n── Test 1: CMU CS admissions page (admissions focus) ─────────")
    result = await tool.fetch_and_extract(
        url="https://csd.cmu.edu/academics/masters/admissions",
        extraction_focus="admissions",
    )
    _print_result(result)
    assert result["success"] or result.get("error"), "Should return success or error"
    if result["success"]:
        data = result["extracted_data"]
        print(f"  GRE required:      {data.get('gre_required')}")
        print(f"  App deadline fall: {data.get('application_deadline_fall')}")
        print(f"  Min GPA:           {data.get('minimum_gpa')}")
        print("  ✓ Admissions extraction completed")


async def test_program(tool) -> None:
    print("\n── Test 2: MIT EECS grad program page (program focus) ────────")
    result = await tool.fetch_and_extract(
        url="https://www.eecs.mit.edu/academics/graduate-programs/",
        extraction_focus="program",
    )
    _print_result(result)
    if result["success"]:
        data = result["extracted_data"]
        print(f"  Program name:  {data.get('program_name')}")
        print(f"  Degree type:   {data.get('degree_type')}")
        print(f"  Duration:      {data.get('duration')}")
        print("  ✓ Program extraction completed")


async def test_error_handling(tool) -> None:
    print("\n── Test 3: 404 page — error handling ─────────────────────────")
    result = await tool.fetch_and_extract(
        url="https://www.cmu.edu/this-page-does-not-exist-xyz123",
        extraction_focus="general",
    )
    print(f"  success: {result['success']}")
    print(f"  error:   {result.get('error')}")
    assert not result["success"], "Should fail gracefully on 404"
    print("  ✓ Error handled gracefully")


async def test_general(tool) -> None:
    print("\n── Test 4: Stanford CS PhD — general focus ───────────────────")
    result = await tool.fetch_and_extract(
        url="https://cs.stanford.edu/academics/phd-program",
        extraction_focus="general",
    )
    _print_result(result)
    if result["success"]:
        print(f"  Extracted keys: {list(result['extracted_data'].keys()) if result['extracted_data'] else 'none'}")
        print("  ✓ General extraction completed")


def _print_result(result: dict) -> None:
    print(f"  URL:             {result['url']}")
    print(f"  Title:           {result.get('page_title') or '(none)'}")
    print(f"  Success:         {result['success']}")
    if not result["success"]:
        print(f"  Error:           {result.get('error')}")
    if result.get("page_text_preview"):
        preview = result["page_text_preview"][:120].replace("\n", " ")
        print(f"  Text preview:    {preview}...")
    if result.get("parse_error"):
        print(f"  Parse error:     {result['parse_error']}")


async def main() -> None:
    from app.tools.page_fetcher import PageFetcherTool

    print("=" * 60)
    print("  Campus Compass — Page Fetcher Tool Smoke Test")
    print("=" * 60)

    tool = PageFetcherTool(anthropic_api_key=API_KEY)

    try:
        await test_admissions(tool)
        await test_error_handling(tool)
        await test_program(tool)
        await test_general(tool)
        print("\n✅  All tests completed\n")
    finally:
        await tool.aclose()


asyncio.run(main())
