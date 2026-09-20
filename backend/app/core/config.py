"""Application settings loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- app ---
    app_name: str = "AutoGrader"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api"

    # --- database (PostgreSQL) ---
    database_url: str = "postgresql+psycopg://autograder:autograder@localhost:5432/autograder"

    # --- auth ---
    jwt_secret: str = "dev-only-secret-key-do-not-use-in-production-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # --- LLM (OpenAI-compatible endpoint, credentials come from .env) ---
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- file storage (uploaded reports) ---
    upload_dir: str = "uploads"

    # --- logging ---
    log_level: str = "INFO"
    log_dir: str = "logs"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
