"""
Quick smoke test for the College Scorecard tool.
Run from backend/: python test_scorecard.py

Reads SCORECARD_API_KEY from .env automatically.
"""

import asyncio
import json
import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SCORECARD_API_KEY", "")
if not API_KEY:
    raise SystemExit(
        "\n❌  SCORECARD_API_KEY is not set.\n"
        "    Add it to backend/.env and rerun.\n"
        "    Free signup: https://api.data.gov/signup/\n"
    )


async def test_search_by_name() -> None:
    from app.tools.scorecard import ScorecardTool

    tool = ScorecardTool(api_key=API_KEY)

    print("\n── Test 1: search by name (Carnegie Mellon) ──────────────────")
    result = await tool.search_institutions(name="Carnegie Mellon", per_page=3)
    print(f"Total results: {result['total_results']}")
    for inst in result["institutions"]:
        print(
            f"  {inst['name']} ({inst['state']}) | {inst['type']} | "
            f"Acceptance: {inst['acceptance_rate_display']} | "
            f"OOS tuition: ${inst['out_of_state_tuition']:,}"
            if inst["out_of_state_tuition"]
            else f"  {inst['name']} ({inst['state']}) | {inst['type']}"
        )
    assert any("Carnegie Mellon" in (i["name"] or "") for i in result["institutions"]), \
        "CMU not found in results!"
    print("  ✓ CMU found")

    await tool.client.aclose()


async def test_detail() -> None:
    from app.tools.scorecard import ScorecardTool

    tool = ScorecardTool(api_key=API_KEY)

    print("\n── Test 2: get_institution_detail for CMU (ID 211440) ────────")
    detail = await tool.get_institution_detail(scorecard_id=211440)

    if "error" in detail:
        print(f"  ⚠️  API returned error: {detail['error']}")
    else:
        print(f"  Name:            {detail['name']}")
        print(f"  Location:        {detail['city']}, {detail['state']}")
        print(f"  Type:            {detail['type']}")
        print(f"  Acceptance rate: {detail['acceptance_rate_display']}")
        print(f"  OOS tuition:     ${detail['out_of_state_tuition']:,}" if detail["out_of_state_tuition"] else "  OOS tuition: N/A")
        print(f"  Avg net price:   ${detail['avg_net_price']:,}" if detail["avg_net_price"] else "  Avg net price: N/A")
        print(f"  Total enroll:    {detail['total_enrollment']:,}" if detail["total_enrollment"] else "  Total enroll: N/A")
        print(f"  Grad enroll:     {detail['graduate_enrollment']:,}" if detail["graduate_enrollment"] else "  Grad enroll: N/A")
        print(f"  Intl students:   {detail['international_student_pct_display']}")
        print(f"  SAT avg:         {detail.get('sat_avg')}")
        print(f"  ACT midpoint:    {detail.get('act_midpoint')}")
        print(f"  Grad rate:       {detail.get('graduation_rate_display')}")
        print(f"  Median earnings (10yr): ${detail.get('median_earnings_10yr'):,}" if detail.get("median_earnings_10yr") else "  Median earnings: N/A")
        programs = detail.get("programs_full", [])[:10]
        print(f"  Programs (first 10): {programs}")
        print("  ✓ Detail fetched successfully")

    await tool.client.aclose()


async def test_filters() -> None:
    from app.tools.scorecard import ScorecardTool

    tool = ScorecardTool(api_key=API_KEY)

    print("\n── Test 3: filter — public CS schools in California ──────────")
    result = await tool.search_institutions(
        state="CA",
        ownership="public",
        has_graduate_programs=True,
        sort_by="enrollment",
        sort_descending=True,
        per_page=5,
    )
    print(f"Total results: {result['total_results']}")
    for inst in result["institutions"]:
        print(
            f"  {inst['name']} | Enroll: {inst['total_enrollment']} | "
            f"OOS: ${inst['out_of_state_tuition']:,}"
            if inst["out_of_state_tuition"]
            else f"  {inst['name']} | Enroll: {inst['total_enrollment']}"
        )
    assert result["total_results"] > 0, "Expected results for CA public schools"
    print("  ✓ Filter query returned results")

    await tool.client.aclose()


async def main() -> None:
    print("=" * 60)
    print("  Campus Compass — College Scorecard Tool Smoke Test")
    print("=" * 60)

    try:
        await test_search_by_name()
        await test_detail()
        await test_filters()
        print("\n✅  All tests passed\n")
    except AssertionError as exc:
        print(f"\n❌  Assertion failed: {exc}\n")
        raise SystemExit(1)
    except Exception as exc:
        print(f"\n❌  Unexpected error: {exc}\n")
        raise


asyncio.run(main())
