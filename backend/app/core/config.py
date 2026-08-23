"""
Centralized settings, loaded from environment variables / .env file.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "SwarmShield"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://swarmshield:swarmshield@localhost:5432/swarmshield"

    # --- Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- Swarm behavior ---
    MAX_ATTACK_ATTEMPTS_PER_VECTOR: int = 5  # cap on adaptive feedback loop retries
    SCAN_TIMEOUT_SECONDS: int = 600

    # --- n8n (optional external orchestration trigger) ---
    N8N_WEBHOOK_URL: str = ""

    # --- GitHub (optional; powers the auto-PR remediation workflow) ---
    # Never hardcode these -- env vars / secrets manager only. A fine-
    # grained PAT scoped to Contents:write + Pull requests:write on the
    # single target repo is the least-privilege choice here (not a
    # classic token with broad repo/admin scope).
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = ""            # "owner/repo"
    GITHUB_BASE_BRANCH: str = "main"
    GITHUB_API_URL: str = "https://api.github.com"

    def github_configured(self) -> bool:
        return bool(self.GITHUB_TOKEN and self.GITHUB_REPO)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
