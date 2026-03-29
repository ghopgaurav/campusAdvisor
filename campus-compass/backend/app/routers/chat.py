import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.orchestrator.agent import CampusCompassAgent
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# Agent is instantiated once and reused across requests
_agent: CampusCompassAgent | None = None


def get_agent() -> CampusCompassAgent:
    global _agent
    if _agent is None:
        _agent = CampusCompassAgent(settings)
    return _agent


AGENT_TIMEOUT_SECONDS = 120


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint. Sends the student's message to the Campus Compass agent.

    The agent will:
    1. Understand the student's question
    2. Decide which tools to use (Scorecard API, web search, page fetcher, etc.)
    3. Call tools as needed to gather information
    4. Synthesize a comprehensive, cited response

    Include student_profile for personalized responses.
    Include conversation_history for multi-turn conversations.
    """
    try:
        agent = get_agent()
        result = await asyncio.wait_for(
            agent.handle_message(request),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        return result
    except asyncio.TimeoutError:
        logger.error("Agent timed out after %ds", AGENT_TIMEOUT_SECONDS)
        raise HTTPException(
            status_code=504,
            detail="The advisor took too long to respond. Please try a simpler question or try again.",
        )
    except Exception as exc:
        logger.exception("Chat error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong processing your message. Please try again.",
        )


@router.get("/test")
async def test_tools() -> dict:
    """Quick sanity check — confirms all tools are initialised and reachable."""
    agent = get_agent()
    tools = agent._tool_registry.get_tool_definitions()
    return {
        "status": "ok",
        "model": agent._model,
        "tools_registered": [t["name"] for t in tools],
        "tool_count": len(tools),
    }


@router.post("/chat/stream")
async def chat_stream(_request: ChatRequest) -> dict:
    """Streaming endpoint — not yet implemented."""
    raise HTTPException(status_code=501, detail="Streaming is not yet implemented.")
