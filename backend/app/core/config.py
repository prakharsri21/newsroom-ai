from functools import lru_cache
from pathlib import Path
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "Newsroom AI"
    app_env: str = "development"

    database_url: str

    openai_api_key: str
    openai_model: str = "gpt-5.6-luna"

    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_base_url: str = "https://cloud.langfuse.com"

    tavily_api_key: str
    firecrawl_api_key: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    os.environ.setdefault(
        "LANGFUSE_PUBLIC_KEY",
        settings.langfuse_public_key,
    )
    os.environ.setdefault(
        "LANGFUSE_SECRET_KEY",
        settings.langfuse_secret_key,
    )
    os.environ.setdefault(
        "LANGFUSE_BASE_URL",
        settings.langfuse_base_url,
    )

    return settings