from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr("postgresql+asyncpg://localhost/ai_study")
    bot_token: SecretStr | None = None
    bot_mode: Literal["polling", "webhook"] = "polling"
    public_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("PUBLIC_BASE_URL", "RENDER_EXTERNAL_URL", "public_base_url"),
    )
    webhook_secret: SecretStr | None = None
    webhook_path: str = "/telegram/webhook"
    admin_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    admin_api_token: SecretStr | None = None
    redis_url: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    transcription_model: str = "gpt-4o-mini-transcribe"
    transcription_enabled: bool = False
    tts_enabled: bool = False
    tts_model: str = "tts-1"
    ai_timeout_seconds: int = Field(default=40, ge=5, le=90)
    ai_max_input_chars: int = Field(default=10000, ge=500, le=20000)
    ai_max_output_tokens: int = Field(default=1100, ge=200, le=3000)
    ai_history_messages: int = Field(default=10, ge=0, le=20)
    ai_history_chars: int = Field(default=12000, ge=0, le=30000)
    ai_free_daily_requests: int = Field(default=3, ge=0, le=100)
    ai_premium_daily_requests: int = Field(default=30, ge=1, le=500)
    ai_user_daily_token_budget: int = Field(default=150000, ge=1000)
    ai_global_daily_token_budget: int = Field(default=2000000, ge=1000)
    rate_limit_per_minute: int = Field(default=30, ge=5, le=300)
    quiz_question_count: int = Field(default=5, ge=1, le=20)
    quiz_seconds_per_question: int = Field(default=90, ge=15, le=600)
    premium_stars: int = Field(default=300, ge=1, le=100000)
    premium_days: int = Field(default=30, ge=1, le=366)
    terms_version: str = Field(default="2026-10-19", min_length=1, max_length=40)
    support_contact: str = "Contact the bot administrator"
    privacy_contact: str = "Contact the bot administrator"
    ai_history_retention_days: int = Field(default=30, ge=1, le=365)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    port: int = Field(default=8000, ge=1, le=65535)

    @field_validator(
        "bot_token",
        "webhook_secret",
        "admin_api_token",
        "redis_url",
        "openai_api_key",
        mode="before",
    )
    @classmethod
    def empty_secrets_are_unset(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value):
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        if raw.startswith(("postgres://", "postgresql://")):
            raw = "postgresql+asyncpg://" + raw.split("://", 1)[1]
        return raw

    @model_validator(mode="after")
    def validate_runtime(self):
        url = self.database_url.get_secret_value()
        if not url.startswith("postgresql+asyncpg://") and not (
            self.app_env == "test" and url.startswith("sqlite+aiosqlite://")
        ):
            raise ValueError("PostgreSQL/asyncpg is required outside tests")
        if self.app_env == "production" and not self.bot_token:
            raise ValueError("BOT_TOKEN is required in production")
        if self.bot_mode == "webhook":
            if not self.public_base_url.startswith("https://"):
                raise ValueError("Webhook mode requires HTTPS PUBLIC_BASE_URL")
            if not self.webhook_secret or len(self.webhook_secret.get_secret_value()) < 32:
                raise ValueError("WEBHOOK_SECRET must contain at least 32 characters")
            import re

            if not re.fullmatch(r"[A-Za-z0-9_-]+", self.webhook_secret.get_secret_value()):
                raise ValueError("WEBHOOK_SECRET must use letters, digits, underscores or hyphens")
        if not self.webhook_path.startswith("/") or "?" in self.webhook_path:
            raise ValueError("WEBHOOK_PATH must be an absolute path")
        if self.admin_api_token and len(self.admin_api_token.get_secret_value()) < 32:
            raise ValueError("ADMIN_API_TOKEN must contain at least 32 characters")
        if self.transcription_enabled or self.tts_enabled:
            if not self.openai_api_key:
                raise ValueError("Audio features require OPENAI_API_KEY")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
