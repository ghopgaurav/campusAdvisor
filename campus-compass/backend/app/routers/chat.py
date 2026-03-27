import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.orchestrator.agent import run_agent
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

AGENT_TIMEOUT_SECONDS = 120


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await asyncio.wait_for(
            run_agent(request),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        return result
    except asyncio.TimeoutError:
        logger.error("Agent loop timed out after %ds", AGENT_TIMEOUT_SECONDS)
        raise HTTPException(
            status_code=504,
            detail="The advisor took too long to respond. Please try a simpler question or try again.",
        )
    except Exception as exc:
        logger.exception("Unexpected error in agent loop: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing your request. Please try again.",
        )


@router.post("/chat/stream")
async def chat_stream(_request: ChatRequest) -> JSONResponse:
    """Streaming endpoint — not yet implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Streaming is not yet implemented."},
    )
