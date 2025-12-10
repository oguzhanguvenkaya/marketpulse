import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    BRIGHT_API_KEY: str = os.getenv("BRIGHT_API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    class Config:
        env_file = ".env"

settings = Settings()
