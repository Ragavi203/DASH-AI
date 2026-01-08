from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "./uploads"
    report_dir: str = "./reports"
    allowed_origins: str = "http://localhost:3000"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1"
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str | None = None

    def ensure_dirs(self) -> None:
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.report_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s



