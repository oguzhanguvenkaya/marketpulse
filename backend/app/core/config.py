import os
from pydantic_settings import BaseSettings
from typing import Optional, Literal, List

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "")
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    BRIGHT_DATA_ACCOUNT_ID: str = os.getenv("BRIGHT_DATA_ACCOUNT_ID", "")
    BRIGHT_DATA_ZONE_NAME: str = os.getenv("BRIGHT_DATA_ZONE_NAME", "")
    BRIGHT_DATA_ZONE_PASSWORD: str = os.getenv("BRIGHT_DATA_ZONE_PASSWORD", "")
    
    SCRAPER_API_KEY: str = os.getenv("SCRAPPER_API", "")
    
    PROXY_PROVIDER: str = os.getenv("PROXY_PROVIDER", "auto")
    
    DEBUG_SAVE_HTML: bool = os.getenv("DEBUG_SAVE_HTML", "true").lower() == "true"
    DEBUG_HTML_PATH: str = os.getenv("DEBUG_HTML_PATH", "/tmp/scraping_debug")
    
    @property
    def bright_data_proxy_config(self) -> Optional[dict]:
        if self.BRIGHT_DATA_ACCOUNT_ID and self.BRIGHT_DATA_ZONE_PASSWORD:
            zone_name = self.BRIGHT_DATA_ZONE_NAME.strip() if self.BRIGHT_DATA_ZONE_NAME else ""
            if zone_name and zone_name.lower() not in ["zone_name", "", "empty", "none"]:
                zone_part = f"-zone-{zone_name}"
            else:
                zone_part = ""
            return {
                "server": "http://brd.superproxy.io:33335",
                "username": f"brd-customer-{self.BRIGHT_DATA_ACCOUNT_ID}{zone_part}",
                "password": self.BRIGHT_DATA_ZONE_PASSWORD
            }
        return None
    
    @property
    def scraper_api_proxy_config(self) -> Optional[dict]:
        if self.SCRAPER_API_KEY:
            return {
                "server": "http://proxy-server.scraperapi.com:8001",
                "username": "scraperapi.render=true.country_code=tr",
                "password": self.SCRAPER_API_KEY
            }
        return None
    
    @property
    def scraper_api_premium_proxy_config(self) -> Optional[dict]:
        if self.SCRAPER_API_KEY:
            return {
                "server": "http://proxy-server.scraperapi.com:8001",
                "username": "scraperapi.render=true.premium=true.country_code=tr",
                "password": self.SCRAPER_API_KEY
            }
        return None
    
    def has_scraper_api(self) -> bool:
        return bool(self.SCRAPER_API_KEY)
    
    def has_bright_data(self) -> bool:
        return bool(self.BRIGHT_DATA_ACCOUNT_ID and self.BRIGHT_DATA_ZONE_PASSWORD)

    def require_database_url(self) -> str:
        db_url = (self.DATABASE_URL or "").strip()
        if not db_url:
            raise ValueError(
                "DATABASE_URL is not set. Configure it in environment variables or backend/.env before starting the backend."
            )
        return db_url

    def require_internal_api_key(self) -> str:
        api_key = (self.INTERNAL_API_KEY or "").strip()
        if not api_key:
            raise ValueError(
                "INTERNAL_API_KEY is not set. Configure it in environment variables or backend/.env before starting the backend."
            )
        return api_key

    def cors_allowed_origins(self) -> List[str]:
        origins = [origin.strip() for origin in (self.CORS_ALLOWED_ORIGINS or "").split(",") if origin.strip()]
        if not origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one allowed origin.")
        return origins
    
    class Config:
        env_file = ".env"

settings = Settings()
