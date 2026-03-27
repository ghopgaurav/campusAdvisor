import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Campus Compass API",
    description="AI-powered graduate school advisor",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Campus Compass API is running")
    logger.info("Model: %s", settings.ANTHROPIC_MODEL)
