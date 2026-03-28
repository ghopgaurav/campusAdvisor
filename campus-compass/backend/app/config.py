from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AWS credentials for Bedrock — required at request time (lazy validation)
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"

    # Bedrock model IDs — use cross-region inference profile prefix "us."
    ANTHROPIC_MODEL: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    ANTHROPIC_MODEL_CHEAP: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

    MAX_TOOL_CALLS_PER_TURN: int = 15
    LOG_LEVEL: str = "INFO"

    # College Scorecard API key (optional at startup)
    SCORECARD_API_KEY: str | None = None

    def require_aws_credentials(self) -> tuple[str, str]:
        """Return (access_key, secret_key) or raise if either is missing."""
        if not self.AWS_ACCESS_KEY_ID or not self.AWS_SECRET_ACCESS_KEY:
            raise RuntimeError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env "
                "to use Claude via Bedrock."
            )
        return self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY

    def require_scorecard_key(self) -> str:
        if not self.SCORECARD_API_KEY:
            raise RuntimeError(
                "SCORECARD_API_KEY is not set. Add it to your .env file. "
                "Free signup: https://api.data.gov/signup/"
            )
        return self.SCORECARD_API_KEY


settings = Settings()
