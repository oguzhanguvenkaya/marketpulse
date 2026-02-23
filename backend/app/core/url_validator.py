import socket
import ipaddress
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}


def validate_url_safe(url: str) -> tuple[bool, str]:
    """
    Validate that a URL is safe to scrape (not targeting private/local IPs).
    Returns (is_safe, error_message).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Gecersiz URL formati"

    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, "Sadece HTTP/HTTPS desteklenir"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL'de hostname bulunamadi"

    try:
        resolved_ip = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(resolved_ip)
    except (socket.gaierror, ValueError):
        return False, "Hostname cozumlenemedi"

    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        logger.warning(f"SSRF attempt blocked: {url} -> {resolved_ip}")
        return False, "Private/local adresler desteklenmez"

    return True, ""
