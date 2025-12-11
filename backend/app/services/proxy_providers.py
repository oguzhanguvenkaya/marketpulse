from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.core.config import settings
import os
from datetime import datetime

class ProxyProvider(ABC):
    name: str = "base"
    
    @abstractmethod
    def get_proxy_config(self, premium: bool = False) -> Optional[Dict[str, str]]:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    def get_description(self) -> str:
        return f"{self.name} proxy provider"


class ScraperAPIProvider(ProxyProvider):
    name = "scraperapi"
    
    def get_proxy_config(self, premium: bool = False) -> Optional[Dict[str, str]]:
        if not self.is_available():
            return None
        
        if premium:
            return settings.scraper_api_premium_proxy_config
        return settings.scraper_api_proxy_config
    
    def is_available(self) -> bool:
        return settings.has_scraper_api()
    
    def get_description(self) -> str:
        return "ScraperAPI Proxy (Ucuz, JavaScript rendering destekli)"


class BrightDataProvider(ProxyProvider):
    name = "brightdata"
    
    def get_proxy_config(self, premium: bool = False) -> Optional[Dict[str, str]]:
        if not self.is_available():
            return None
        return settings.bright_data_proxy_config
    
    def is_available(self) -> bool:
        return settings.has_bright_data()
    
    def get_description(self) -> str:
        return "Bright Data Residential Proxy (Premium, en guvenilir)"


class DirectProvider(ProxyProvider):
    name = "direct"
    
    def get_proxy_config(self, premium: bool = False) -> Optional[Dict[str, str]]:
        return None
    
    def is_available(self) -> bool:
        return True
    
    def get_description(self) -> str:
        return "Dogrudan baglanti (proxy yok)"


class ProxyManager:
    def __init__(self):
        self.providers = {
            "scraperapi": ScraperAPIProvider(),
            "brightdata": BrightDataProvider(),
            "direct": DirectProvider()
        }
        self.current_provider: Optional[str] = None
        self.fallback_chain = ["scraperapi", "brightdata", "direct"]
    
    def get_provider(self, name: str) -> Optional[ProxyProvider]:
        return self.providers.get(name)
    
    def get_available_providers(self) -> list:
        return [
            {"name": name, "available": p.is_available(), "description": p.get_description()}
            for name, p in self.providers.items()
        ]
    
    def get_primary_provider(self) -> ProxyProvider:
        provider_setting = settings.PROXY_PROVIDER
        
        if provider_setting == "auto":
            for name in self.fallback_chain:
                provider = self.providers.get(name)
                if provider and provider.is_available():
                    self.current_provider = name
                    return provider
            return self.providers["direct"]
        
        provider = self.providers.get(provider_setting)
        if provider and provider.is_available():
            self.current_provider = provider_setting
            return provider
        
        return self.providers["direct"]
    
    def get_fallback_provider(self, current: str) -> Optional[ProxyProvider]:
        try:
            current_idx = self.fallback_chain.index(current)
            for name in self.fallback_chain[current_idx + 1:]:
                provider = self.providers.get(name)
                if provider and provider.is_available():
                    self.current_provider = name
                    return provider
        except ValueError:
            pass
        return None
    
    def get_proxy_config(self, provider_name: Optional[str] = None, premium: bool = False) -> Optional[Dict[str, str]]:
        if provider_name:
            provider = self.providers.get(provider_name)
            if provider and provider.is_available():
                return provider.get_proxy_config(premium)
        
        primary = self.get_primary_provider()
        return primary.get_proxy_config(premium)


class DebugLogger:
    def __init__(self):
        self.debug_path = settings.DEBUG_HTML_PATH
        self.save_html = settings.DEBUG_SAVE_HTML
        os.makedirs(self.debug_path, exist_ok=True)
    
    def log_request(self, url: str, provider: str, status: int, message: str = ""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] Provider: {provider} | URL: {url[:80]}... | Status: {status} | {message}"
        print(log_entry)
        
        log_file = os.path.join(self.debug_path, "scraping.log")
        with open(log_file, "a") as f:
            f.write(log_entry + "\n")
    
    def save_debug_html(self, url: str, html_content: str, status: int, provider: str):
        if not self.save_html:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_")[:50]
        filename = f"{timestamp}_{status}_{provider}_{safe_url}.html"
        filepath = os.path.join(self.debug_path, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"<!-- URL: {url} -->\n")
            f.write(f"<!-- Status: {status} -->\n")
            f.write(f"<!-- Provider: {provider} -->\n")
            f.write(f"<!-- Timestamp: {timestamp} -->\n")
            f.write(html_content)
        
        print(f"Debug HTML saved: {filepath}")
        return filepath
    
    def log_error(self, url: str, provider: str, error: Exception):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] ERROR | Provider: {provider} | URL: {url[:80]}... | Error: {str(error)}"
        print(log_entry)
        
        log_file = os.path.join(self.debug_path, "scraping_errors.log")
        with open(log_file, "a") as f:
            f.write(log_entry + "\n")


proxy_manager = ProxyManager()
debug_logger = DebugLogger()
