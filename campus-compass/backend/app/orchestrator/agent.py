"""
Main agent loop.
Runs the Claude agentic loop: send message → receive tool calls → execute tools
→ send results back → repeat until Claude returns a final text response.
"""

import logging
from typing import Any

import anthropic

from app.config import settings
from app.orchestrator.system_prompt import build_system_prompt, format_student_profile
from app.orchestrator.tool_registry import TOOL_DEFINITIONS, dispatch_tool
from app.schemas.chat import ChatRequest, ChatResponse, ToolUsageInfo

logger = logging.getLogger(__name__)

def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.require_anthropic_key())


def _build_messages(request: ChatRequest) -> list[dict[str, Any]]:
    """Convert ChatRequest history + current message into Anthropic message format."""
    messages: list[dict[str, Any]] = []

    for msg in request.conversation_history:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": request.message})
    return messages


def _extract_follow_ups(text: str) -> list[str]:
    """
    Heuristically extract follow-up questions from the final response text.
    Looks for lines that end with '?' near the end of the response.
    """
    lines = text.split("\n")
    follow_ups = []
    for line in lines:
        stripped = line.strip().lstrip("-•*123456789. ")
        if stripped.endswith("?") and len(stripped) > 15:
            follow_ups.append(stripped)
    return follow_ups[:3]


async def run_agent(request: ChatRequest) -> ChatResponse:
    """
    Run the full agentic loop for a single user turn.

    1. Build the message list from conversation history + new message.
    2. Call Claude with tools.
    3. If Claude returns tool_use blocks, execute each tool and feed results back.
    4. Repeat until Claude produces a final text response (stop_reason == "end_turn").
    5. Return the final text and tool usage metadata.
    """
    profile_text = format_student_profile(request.student_profile)
    system_prompt = build_system_prompt(profile_text)

    messages = _build_messages(request)
    tools_used: list[ToolUsageInfo] = []
    tool_calls_made = 0

    while tool_calls_made <= settings.MAX_TOOL_CALLS_PER_TURN:
        logger.debug("Agent loop iteration %d", tool_calls_made)

        response = await _get_client().messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        logger.debug("Stop reason: %s", response.stop_reason)

        # --- Final text response ---
        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            follow_ups = _extract_follow_ups(final_text)
            return ChatResponse(
                response=final_text,
                tools_used=tools_used,
                follow_up_suggestions=follow_ups,
            )

        # --- Tool use ---
        if response.stop_reason == "tool_use":
            # Append the assistant's message (which contains tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call and collect results
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_calls_made += 1
                logger.info("Tool call #%d: %s", tool_calls_made, block.name)

                result_json = await dispatch_tool(block.name, block.input)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_json,
                })

                # Track for response metadata
                tools_used.append(ToolUsageInfo(
                    tool_name=block.name,
                    query=(
                        block.input.get("query")
                        or block.input.get("name")      # search_us_universities uses "name"
                        or block.input.get("city")
                        or str(block.input.get("scorecard_id", ""))
                        or block.input.get("url")
                    ),
                    source_url=block.input.get("url"),
                ))

                if tool_calls_made >= settings.MAX_TOOL_CALLS_PER_TURN:
                    logger.warning("Reached MAX_TOOL_CALLS_PER_TURN (%d)", settings.MAX_TOOL_CALLS_PER_TURN)
                    break

            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason — extract whatever text we have and return
            logger.warning("Unexpected stop_reason: %s", response.stop_reason)
            final_text = " ".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            return ChatResponse(response=final_text, tools_used=tools_used)

    # Exceeded max tool calls — ask Claude to wrap up with what it has
    logger.warning("Exceeded max tool calls, requesting final answer")
    messages.append({
        "role": "user",
        "content": "Please provide your best answer based on what you've gathered so far.",
    })
    final_response = await _get_client().messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
    )
    final_text = " ".join(
        block.text for block in final_response.content if hasattr(block, "text")
    )
    return ChatResponse(
        response=final_text,
        tools_used=tools_used,
        follow_up_suggestions=_extract_follow_ups(final_text),
    )
