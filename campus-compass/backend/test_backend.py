"""
End-to-end test script for Campus Compass backend.

Run with the server already running:
    cd backend
    source .venv/bin/activate
    python test_backend.py

Or against Docker:
    docker compose up -d
    python backend/test_backend.py
"""

import asyncio
import json
import sys

import httpx

BASE = "http://localhost:8000"
TIMEOUT = 120.0

PASS = "  ✓"
FAIL = "  ✗"


async def test() -> bool:
    all_passed = True

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:

        # ── Test 1: Health check ──────────────────────────────────────────
        print("Test 1: Health check...")
        try:
            r = await client.get(f"{BASE}/health")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            assert r.json().get("status") == "ok"
            print(f"{PASS} Health check passed")
        except Exception as exc:
            print(f"{FAIL} Health check FAILED: {exc}")
            all_passed = False

        # ── Test 2: Tool registry ─────────────────────────────────────────
        print("Test 2: Tool registry...")
        try:
            r = await client.get(f"{BASE}/api/test")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            assert data["tool_count"] >= 5, f"Expected >= 5 tools, got {data['tool_count']}"
            print(f"{PASS} {data['tool_count']} tools registered: {data['tools_registered']}")
        except Exception as exc:
            print(f"{FAIL} Tool registry FAILED: {exc}")
            all_passed = False

        # ── Test 3: University search (Scorecard API) ─────────────────────
        print("Test 3: University search (triggers Scorecard API)...")
        try:
            r = await client.post(
                f"{BASE}/api/chat",
                json={
                    "message": "What are some affordable public universities in Texas for MS Computer Science?",
                    "student_profile": {
                        "degree_target": "MS",
                        "field_target": "Computer Science",
                        "budget_total_usd": 40000,
                    },
                },
            )
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            assert len(data["response"]) > 100, "Response too short"
            assert len(data["tools_used"]) > 0, "No tools were called"
            tool_names = [t["tool_name"] for t in data["tools_used"]]
            print(f"{PASS} Got response ({len(data['response'])} chars)")
            print(f"{PASS} Tools used: {tool_names}")
        except Exception as exc:
            print(f"{FAIL} University search FAILED: {exc}")
            all_passed = False

        # ── Test 4: Cost of living ────────────────────────────────────────
        print("Test 4: Cost of living query...")
        try:
            r = await client.post(
                f"{BASE}/api/chat",
                json={"message": "How much does it cost to live in Pittsburgh as a student?"},
            )
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            response_lower = data["response"].lower()
            assert (
                "rent" in response_lower or "cost" in response_lower or "$" in data["response"]
            ), "Response doesn't mention costs"
            print(f"{PASS} Got cost info ({len(data['response'])} chars)")
        except Exception as exc:
            print(f"{FAIL} Cost of living FAILED: {exc}")
            all_passed = False

        # ── Test 5: Multi-turn conversation ───────────────────────────────
        print("Test 5: Multi-turn conversation...")
        try:
            r = await client.post(
                f"{BASE}/api/chat",
                json={
                    "message": "Tell me about CMU's MSCS program",
                    "conversation_history": [],
                },
            )
            assert r.status_code == 200, f"Turn 1 expected 200, got {r.status_code}"
            first_response = r.json()["response"]

            r = await client.post(
                f"{BASE}/api/chat",
                json={
                    "message": "What about the tuition and funding options?",
                    "conversation_history": [
                        {"role": "user", "content": "Tell me about CMU's MSCS program"},
                        {"role": "assistant", "content": first_response},
                    ],
                },
            )
            assert r.status_code == 200, f"Turn 2 expected 200, got {r.status_code}"
            data = r.json()
            assert len(data["response"]) > 50, "Follow-up response too short"
            print(f"{PASS} Multi-turn conversation works ({len(data['response'])} chars on turn 2)")
        except Exception as exc:
            print(f"{FAIL} Multi-turn FAILED: {exc}")
            all_passed = False

        # ── Test 6: Follow-up suggestions ────────────────────────────────
        print("Test 6: Follow-up suggestions present...")
        try:
            r = await client.post(
                f"{BASE}/api/chat",
                json={"message": "What is the tuition at Georgia Tech for MSCS?"},
            )
            assert r.status_code == 200
            data = r.json()
            assert isinstance(data["follow_up_suggestions"], list)
            print(
                f"{PASS} Follow-up suggestions: {data['follow_up_suggestions']}"
            )
        except Exception as exc:
            print(f"{FAIL} Follow-up suggestions FAILED: {exc}")
            all_passed = False

    return all_passed


if __name__ == "__main__":
    print(f"\n{'='*50}")
    print("Campus Compass — Backend Integration Tests")
    print(f"Target: {BASE}")
    print(f"{'='*50}\n")

    passed = asyncio.run(test())

    print()
    if passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed — check output above.")
        sys.exit(1)
