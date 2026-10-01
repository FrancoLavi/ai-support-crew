"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    """Small, typed configuration object for the application."""

    app_name: str = Field(default="AI Support Crew")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    llm_provider: str = Field(default="litellm")
    llm_model: str = Field(default="gemini/gemini-3.5-flash-lite")
    llm_api_key: str | None = Field(default=None)
    aws_region: str | None = Field(default=None)
    bedrock_model_id: str | None = Field(default=None)
    llm_max_retries: int = Field(default=5, ge=1, le=10)
    llm_retry_base_delay: float = Field(default=2.0, gt=0.0, le=60.0)


def get_settings() -> Settings:
    """Build settings from environment variables."""

    return Settings(
        app_name=os.getenv("APP_NAME", "AI Support Crew"),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        llm_provider=os.getenv("LLM_PROVIDER", "litellm"),
        llm_model=os.getenv("LLM_MODEL", "gemini/gemini-3.5-flash-lite"),
        llm_api_key=os.getenv("GEMINI_API_KEY"),
        aws_region=os.getenv("AWS_REGION"),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID"),
        llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", "5")),
        llm_retry_base_delay=float(os.getenv("LLM_RETRY_BASE_DELAY", "2")),
    )


def active_llm_provider(settings: Settings | None = None) -> str:
    """Return the concrete provider used for user-facing error handling."""

    resolved = settings or get_settings()
    configured = resolved.llm_provider.strip().lower()
    model = resolved.llm_model.strip().lower()
    if configured in {"bedrock", "aws-bedrock"} or model.startswith("bedrock/"):
        return "bedrock"
    if configured in {"gemini", "google", "litellm"} or model.startswith("gemini/"):
        return "gemini"
    return configured
