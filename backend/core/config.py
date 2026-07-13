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
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    class Config:
        env_file = "backend/.env"


settings = Settings()