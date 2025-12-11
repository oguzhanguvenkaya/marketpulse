import os
from pydantic_settings import BaseSettings
from typing import Optional, Literal

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
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
    
    class Config:
        env_file = ".env"

settings = Settings()
