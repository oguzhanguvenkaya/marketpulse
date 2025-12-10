import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    BRIGHT_DATA_ACCOUNT_ID: str = os.getenv("BRIGHT_DATA_ACCOUNT_ID", "")
    BRIGHT_DATA_ZONE_NAME: str = os.getenv("BRIGHT_DATA_ZONE_NAME", "")
    BRIGHT_DATA_ZONE_PASSWORD: str = os.getenv("BRIGHT_DATA_ZONE_PASSWORD", "")
    
    @property
    def bright_data_proxy_config(self):
        if self.BRIGHT_DATA_ACCOUNT_ID and self.BRIGHT_DATA_ZONE_PASSWORD:
            zone_part = f"-zone-{self.BRIGHT_DATA_ZONE_NAME}" if self.BRIGHT_DATA_ZONE_NAME else ""
            return {
                "server": "http://brd.superproxy.io:33335",
                "username": f"brd-customer-{self.BRIGHT_DATA_ACCOUNT_ID}{zone_part}",
                "password": self.BRIGHT_DATA_ZONE_PASSWORD
            }
        return None
    
    class Config:
        env_file = ".env"

settings = Settings()
