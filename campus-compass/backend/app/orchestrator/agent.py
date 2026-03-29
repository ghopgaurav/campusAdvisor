"""
Main agent loop — CampusCompassAgent.

Handles the full conversation cycle:
  user message → Claude (with tools) → tool calls → results → … → final answer

The module also exports a top-level run_agent() shim so that routers/chat.py
doesn't need to be touched.
"""

import json
import logging
from typing import Any

from anthropic import AsyncAnthropicBedrock, APIError, APITimeoutError

from app.config import Settings, settings as _default_settings
from app.orchestrator.system_prompt import build_system_prompt
from app.orchestrator.tool_registry import ToolRegistry
from app.schemas.chat import ChatRequest, ChatResponse, ToolUsageInfo

logger = logging.getLogger(__name__)


class CampusCompassAgent:
    """
    Wraps the Claude agentic loop with tool execution, error handling,
    per-turn tool-call limits, and heuristic follow-up suggestions.
    """

    def __init__(self, config: Settings) -> None:
        self._config = config
        self._model = config.ANTHROPIC_MODEL
        self._max_tool_calls = config.MAX_TOOL_CALLS_PER_TURN
        self._tool_registry = ToolRegistry(config)

    def _get_client(self) -> AsyncAnthropicBedrock:
        access_key, secret_key = self._config.require_aws_credentials()
        return AsyncAnthropicBedrock(
            aws_access_key=access_key,
            aws_secret_key=secret_key,
            aws_region=self._config.AWS_REGION,
        )

    def _build_messages(self, request: ChatRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for msg in request.conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": request.message})
        return messages

    def _generate_follow_ups(self, request: ChatRequest, response: str) -> list[str]:
        """Generate contextual follow-up suggestions via simple keyword heuristics."""
        suggestions: list[str] = []
        lower = response.lower()

        if "tuition" in lower or "cost" in lower:
            suggestions.append("What about living costs in that city?")
            suggestions.append("Are there scholarships or assistantships available?")

        if "gre" in lower or "toefl" in lower or "requirement" in lower:
            suggestions.append("How competitive is my profile for this program?")
            suggestions.append("Can you compare this with similar programs?")

        if "deadline" in lower:
            suggestions.append("What materials do I need for the application?")

        if any(w in lower for w in ("compare", " vs ", "versus", "difference")):
            suggestions.append("Which one would you recommend given my profile?")
            suggestions.append("What are the living costs at each location?")

        if "visa" in lower or "f-1" in lower or "opt" in lower:
            suggestions.append("What's the OPT/STEM OPT timeline after graduation?")

        if not suggestions:
            suggestions = [
                "Can you find more programs that match my profile?",
                "What are my chances at this program?",
                "Tell me about student life at this university",
            ]

        return suggestions[:3]

    async def handle_message(self, request: ChatRequest) -> ChatResponse:
        """
        Run the full agentic loop for one user turn.

        1. Build system prompt (with optional student profile).
        2. Build message list from history + new message.
        3. Enter the Claude ↔ tool loop until end_turn or max tool calls.
        4. Return ChatResponse with the final text, tools used, and follow-ups.
        """
        system_prompt = build_system_prompt(request.student_profile)
        messages = self._build_messages(request)
        tools = self._tool_registry.get_tool_definitions()
        tools_used: list[ToolUsageInfo] = []
        tool_call_count = 0
        client = self._get_client()

        try:
            while True:
                logger.debug(
                    "Agent loop iteration %d/%d", tool_call_count, self._max_tool_calls
                )

                try:
                    response = await client.messages.create(
                        model=self._model,
                        max_tokens=4096,
                        system=system_prompt,
                        messages=messages,
                        tools=tools,
                    )
                except APITimeoutError as exc:
                    logger.error("Bedrock API timeout: %s", exc)
                    return ChatResponse(
                        response=(
                            "I'm sorry — the AI service took too long to respond. "
                            "Please try again with a simpler question."
                        ),
                        tools_used=tools_used,
                        follow_up_suggestions=[],
                    )
                except APIError as exc:
                    logger.error("Bedrock API error: %s", exc)
                    return ChatResponse(
                        response=(
                            "I encountered an issue connecting to the AI service. "
                            "Please try again in a moment."
                        ),
                        tools_used=tools_used,
                        follow_up_suggestions=[],
                    )

                logger.debug("Stop reason: %s", response.stop_reason)

                # ── Final answer ───────────────────────────────────────────
                if response.stop_reason == "end_turn":
                    final_text = "".join(
                        block.text
                        for block in response.content
                        if hasattr(block, "text")
                    )
                    return ChatResponse(
                        response=final_text,
                        tools_used=tools_used,
                        follow_up_suggestions=self._generate_follow_ups(request, final_text),
                    )

                # ── Tool calls ─────────────────────────────────────────────
                if response.stop_reason == "tool_use":
                    tool_use_blocks = [
                        b for b in response.content if b.type == "tool_use"
                    ]

                    # Append assistant turn (contains the tool_use blocks)
                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = []
                    for block in tool_use_blocks:
                        tool_call_count += 1

                        if tool_call_count > self._max_tool_calls:
                            logger.warning(
                                "Max tool calls (%d) reached — sending cap notice",
                                self._max_tool_calls,
                            )
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": (
                                    "Maximum tool calls reached for this query. "
                                    "Please provide your best answer with the information gathered so far."
                                ),
                            })
                            continue

                        input_summary = json.dumps(block.input)[:200]
                        logger.info(
                            "Tool call #%d: %s | input: %s",
                            tool_call_count,
                            block.name,
                            input_summary,
                        )

                        # Execute — ToolRegistry handles per-call timeout + errors
                        result = await self._tool_registry.execute_tool(
                            block.name, block.input
                        )

                        tools_used.append(ToolUsageInfo(
                            tool_name=block.name,
                            query=(
                                block.input.get("query")
                                or block.input.get("name")
                                or block.input.get("city")
                                or block.input.get("url")
                                or str(block.input.get("scorecard_id", ""))
                                or input_summary
                            ),
                            source_url=block.input.get("url"),
                        ))

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                    # Feed all results back to Claude in one user turn
                    messages.append({"role": "user", "content": tool_results})

                    # If we've hit the cap, ask Claude to wrap up
                    if tool_call_count >= self._max_tool_calls:
                        logger.warning(
                            "Tool call cap hit (%d), requesting final synthesis",
                            self._max_tool_calls,
                        )
                        messages.append({
                            "role": "user",
                            "content": (
                                "Please provide your best answer based on "
                                "the information gathered so far."
                            ),
                        })
                        try:
                            final_response = await client.messages.create(
                                model=self._model,
                                max_tokens=4096,
                                system=system_prompt,
                                messages=messages,
                            )
                            final_text = "".join(
                                b.text
                                for b in final_response.content
                                if hasattr(b, "text")
                            )
                        except Exception as exc:
                            logger.error("Final synthesis call failed: %s", exc)
                            final_text = (
                                "I gathered some information but ran into an issue "
                                "synthesizing it. Please try a more focused question."
                            )
                        return ChatResponse(
                            response=final_text,
                            tools_used=tools_used,
                            follow_up_suggestions=self._generate_follow_ups(request, final_text),
                        )

                    # Otherwise continue the loop
                    continue

                # ── Unexpected stop reason ─────────────────────────────────
                else:
                    logger.warning("Unexpected stop reason: %s", response.stop_reason)
                    final_text = " ".join(
                        b.text for b in response.content if hasattr(b, "text")
                    )
                    return ChatResponse(
                        response=final_text or "I encountered an unexpected issue. Please try again.",
                        tools_used=tools_used,
                        follow_up_suggestions=[],
                    )

        except Exception as exc:
            logger.exception("Unhandled error in agent loop: %s", exc)
            return ChatResponse(
                response=(
                    "Something went wrong while processing your request. "
                    "Please try again."
                ),
                tools_used=tools_used,
                follow_up_suggestions=[],
            )


# ---------------------------------------------------------------------------
# Module-level shim — keeps routers/chat.py working without changes
# ---------------------------------------------------------------------------

_agent: CampusCompassAgent | None = None


def _get_agent() -> CampusCompassAgent:
    global _agent
    if _agent is None:
        _agent = CampusCompassAgent(_default_settings)
    return _agent


async def run_agent(request: ChatRequest) -> ChatResponse:
    """Top-level entry point called by the chat router."""
    return await _get_agent().handle_message(request)
