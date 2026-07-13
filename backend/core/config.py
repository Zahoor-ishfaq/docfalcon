"""App config from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    POPPLER_PATH: str = ""

    # LLM
    LLM_PROVIDER: str = "claude"  # claude | groq
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    MONGODB_URL: str = ""

    class Config:
        env_file = ".env"


settings = Settings()