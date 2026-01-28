import logging
import sys
import re
from typing import Optional


class PollingLogFilter(logging.Filter):
    """Filter to suppress noisy polling endpoint logs"""
    
    POLLING_PATTERNS = [
        r'GET /api/price-monitor/fetch/[A-Fa-f0-9-]+ HTTP/1\.[01]',
    ]
    
    def __init__(self):
        super().__init__()
        self.compiled_patterns = [re.compile(p) for p in self.POLLING_PATTERNS]
    
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                return False
        return True


_uvicorn_filter_applied = False

def setup_uvicorn_log_filter():
    """Apply polling filter to uvicorn access logger (only once)"""
    global _uvicorn_filter_applied
    if _uvicorn_filter_applied:
        return
    _uvicorn_filter_applied = True
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.addFilter(PollingLogFilter())


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get or create a logger with standardized format.
    
    Args:
        name: Logger name (typically module name like 'scraping', 'price_monitor')
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger


scraping_logger = get_logger('scraping')
price_monitor_logger = get_logger('price_monitor')
api_logger = get_logger('api')
proxy_logger = get_logger('proxy')
