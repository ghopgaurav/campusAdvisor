from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ANTHROPIC_API_KEY: str
    SCORECARD_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    MAX_TOOL_CALLS_PER_TURN: int = 15
    LOG_LEVEL: str = "INFO"


settings = Settings()
