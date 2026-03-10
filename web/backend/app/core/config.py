from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _default_database_url() -> str:
    db_path = (BACKEND_DIR / "web_app.db").resolve()
    path_str = db_path.as_posix()
    if db_path.drive:
        return f"sqlite:///{path_str}"
    return f"sqlite:////{path_str}"


class Settings(BaseSettings):
    app_name: str = "Auto-reg Web"
    api_v1_prefix: str = "/api"
    secret_key: str = "change-me-in-env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 30
    database_url: str = Field(default_factory=_default_database_url)
    mail_tm_api_url: str = "https://api.mail.tm"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    cors_origin_regex: str | None = r"^https?://.*$"

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
