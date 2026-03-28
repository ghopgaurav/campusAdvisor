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
    logger.info("Campus Compass API is running (via AWS Bedrock)")
    logger.info("Main model:  %s", settings.ANTHROPIC_MODEL)
    logger.info("Cheap model: %s", settings.ANTHROPIC_MODEL_CHEAP)
    logger.info("AWS region:  %s", settings.AWS_REGION)
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning("AWS credentials not set — chat requests will fail until added to .env")
    if not settings.SCORECARD_API_KEY:
        logger.warning("SCORECARD_API_KEY is not set — college_scorecard tool will fail until it is added to .env")
