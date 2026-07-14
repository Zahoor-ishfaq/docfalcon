"""App config from environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="backend/.env", extra="ignore")

    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    POPPLER_PATH: str = ""

    # LLM
    LLM_PROVIDER: str = "claude"  # claude | groq
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    MONGODB_URL: str = ""
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    REDIS_URL: str = ""
    REDIS_TOKEN: str = ""

    # RAG
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # Tracing
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _lock_down_prod(self):
        """Fail fast at boot rather than shipping a permissive prod config."""
        if self.is_prod:
            if not self.origins:
                raise ValueError("ALLOWED_ORIGINS is required in production")
            if any(o == "*" or "localhost" in o or "127.0.0.1" in o for o in self.origins):
                raise ValueError("ALLOWED_ORIGINS must not contain '*' or localhost in production")
            if len(self.JWT_SECRET) < 32:
                raise ValueError("JWT_SECRET must be at least 32 chars in production")
        return self


settings = Settings()