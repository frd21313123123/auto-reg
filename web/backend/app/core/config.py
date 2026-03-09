import secrets
import warnings
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _generate_secret() -> str:
    warnings.warn(
        "AUTO_REG_SECRET_KEY is not set — using a random ephemeral secret. "
        "All existing tokens will be invalidated on restart. "
        "Set AUTO_REG_SECRET_KEY in your .env file for production.",
        stacklevel=2,
    )
    return secrets.token_hex(32)


class Settings(BaseSettings):
    app_name: str = "Auto-reg Web"
    api_v1_prefix: str = "/api"
    secret_key: str = Field(default_factory=_generate_secret)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./web_app.db"
    mail_tm_api_url: str = "https://api.mail.tm"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    cors_origin_regex: str | None = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    model_config = SettingsConfigDict(
        env_prefix="AUTO_REG_",
        env_file=".env",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
