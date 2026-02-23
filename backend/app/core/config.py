from __future__ import annotations

import logging
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List

logger = logging.getLogger(__name__)

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
_SCRAPER_KEY_NAMES = ("SCRAPER_API_KEY", "SCRAPPER_API", "SCRAPPPER_API")


def _normalize_secret(value: str) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _read_env_value_from_file(env_file: Path, key_names: tuple[str, ...]) -> str:
    if not env_file.exists():
        return ""

    try:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() in key_names:
                normalized = _normalize_secret(value)
                if normalized:
                    return normalized
    except Exception:
        return ""

    return ""


def _resolve_scraper_api_key() -> str:
    for key_name in _SCRAPER_KEY_NAMES:
        value = _normalize_secret(os.getenv(key_name, ""))
        if value:
            return value

    for env_file in (_ENV_FILE, _BACKEND_ENV_FILE):
        value = _read_env_value_from_file(env_file, _SCRAPER_KEY_NAMES)
        if value:
            return value

    for secret_file in (
        "/etc/secrets/SCRAPER_API_KEY",
        "/etc/secrets/SCRAPPER_API",
        "/etc/secrets/SCRAPPPER_API",
    ):
        try:
            value = _normalize_secret(Path(secret_file).read_text(encoding="utf-8"))
            if value:
                return value
        except Exception:
            continue

    return ""

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "")
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    PRICE_MONITOR_EXECUTOR: str = os.getenv("PRICE_MONITOR_EXECUTOR", "celery")
    PRICE_MONITOR_MAX_CONCURRENT_REQUESTS: int = _env_int("PRICE_MONITOR_MAX_CONCURRENT_REQUESTS", 40)
    DB_POOL_SIZE: int = _env_int("DB_POOL_SIZE", 10)
    DB_MAX_OVERFLOW: int = _env_int("DB_MAX_OVERFLOW", 20)
    DB_POOL_TIMEOUT_SECONDS: int = _env_int("DB_POOL_TIMEOUT_SECONDS", 30)
    DB_POOL_RECYCLE_SECONDS: int = _env_int("DB_POOL_RECYCLE_SECONDS", 180)
    
    BRIGHT_DATA_ACCOUNT_ID: str = os.getenv("BRIGHT_DATA_ACCOUNT_ID", "")
    BRIGHT_DATA_ZONE_NAME: str = os.getenv("BRIGHT_DATA_ZONE_NAME", "")
    BRIGHT_DATA_ZONE_PASSWORD: str = os.getenv("BRIGHT_DATA_ZONE_PASSWORD", "")
    
    SCRAPER_API_KEY: str = _resolve_scraper_api_key()
    
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
                "username": "scraperapi.render=true.country_code=eu",
                "password": self.SCRAPER_API_KEY
            }
        return None
    
    @property
    def scraper_api_premium_proxy_config(self) -> Optional[dict]:
        if self.SCRAPER_API_KEY:
            return {
                "server": "http://proxy-server.scraperapi.com:8001",
                "username": "scraperapi.render=true.premium=true.country_code=eu",
                "password": self.SCRAPER_API_KEY
            }
        return None
    
    def has_scraper_api(self) -> bool:
        return bool((self.SCRAPER_API_KEY or "").strip())
    
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

    def require_scraper_api_key(self) -> str:
        api_key = (self.SCRAPER_API_KEY or "").strip()
        if not api_key:
            raise ValueError(
                "SCRAPER_API_KEY is not set. Configure SCRAPER_API_KEY (or SCRAPPER_API/SCRAPPPER_API) in environment variables or .env before starting fetch operations."
            )
        return api_key

    def price_monitor_executor(self) -> str:
        raw = (self.PRICE_MONITOR_EXECUTOR or "").strip().lower()
        if raw in {"local", "celery"}:
            return raw
        return "celery"

    def cors_allowed_origins(self) -> List[str]:
        raw = (self.CORS_ALLOWED_ORIGINS or "").strip()
        if raw == "*":
            return ["*"]
        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        replit_domains = os.getenv("REPLIT_DOMAINS", "")
        if replit_domains:
            for domain in replit_domains.split(","):
                d = domain.strip()
                if d:
                    https_origin = f"https://{d}"
                    if https_origin not in origins:
                        origins.append(https_origin)
        if not origins:
            logger.warning("CORS: No origins configured and no REPLIT_DOMAINS found")
        return origins
    
    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"

settings = Settings()
