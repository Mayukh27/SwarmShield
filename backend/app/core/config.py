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

    # --- Local-first LLM routing ---
    LLM_PROVIDER: str = "auto"  # auto, local, gemini, grok
    LOCAL_LLM_ENABLED: bool = True
    LOCAL_LLM_PROVIDER: str = "ollama"
    LOCAL_LLM_MODEL: str = ""
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434"
    GROK_ENABLED: bool = False
    GROK_API_KEY: str = ""
    GROK_MODEL: str = ""
    GROK_BASE_URL: str = "https://api.x.ai/v1"
    LLM_CLOUD_FALLBACK: bool = True
    LLM_CONFIDENCE_THRESHOLD: float = 0.80
    LLM_MEDIUM_CONFIDENCE_THRESHOLD: float = 0.60
    LOCAL_LLM_MAX_CONTEXT_TOKENS: int = 4000
    LOCAL_LLM_MAX_OUTPUT_TOKENS: int = 1000
    MAX_LOCAL_LLM_CONCURRENCY: int = 2
    MAX_CLOUD_LLM_CONCURRENCY: int = 1
    MAX_LOCAL_LLM_CALLS_PER_SCAN: int = 100
    MAX_CLOUD_LLM_CALLS_PER_SCAN: int = 5
    MAX_CLOUD_LLM_CALLS_PER_MINUTE: int = 5

    # --- Local RAG and persistent intelligence ---
    RAG_ENABLED: bool = True
    RAG_TOP_K: int = 6
    RAG_MAX_CONTEXT_TOKENS: int = 3500
    MAX_RAG_QUERIES_PER_SCAN: int = 50
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    MEMORY_ENABLED: bool = True
    MEMORY_MIN_IMPORTANCE: float = 0.60
    LLM_CACHE_ENABLED: bool = True

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
