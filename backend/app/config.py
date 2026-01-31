from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # We load .env manually in get_settings() so missing/unreadable env files don't break
    # Alembic migrations / CI / production containers.
    model_config = SettingsConfigDict(extra="ignore")

    app_env: str = "dev"
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "./uploads"
    report_dir: str = "./reports"
    allowed_origins: str = "http://localhost:3000"

    jwt_secret: str = "dev-secret-change-me"
    jwt_exp_minutes: int = 60 * 24 * 14  # 14 days

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_prompt_version: str = "v1"
    openai_timeout_s: float = 25.0
    openai_max_tokens: int = 700

    llm_max_sample_rows: int = 20
    llm_max_columns: int = 45
    anthropic_api_key: str | None = None

    upload_async_threshold_bytes: int = 5_000_000

    def ensure_dirs(self) -> None:
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.report_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    try:
        from dotenv import load_dotenv

        load_dotenv(".env", override=False)
    except Exception:
        pass
    s = Settings()
    s.ensure_dirs()
    return s



