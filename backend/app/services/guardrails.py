"""Input guardrails — kullanici mesajlarini guvenlik kontrolleri.

Regex tabanli kontroller:
- SQL injection pattern'leri
- Script tag'leri (XSS)
- Prompt injection pattern'leri
- Mesaj uzunluk siniri
"""
from __future__ import annotations

import re
from typing import Tuple

# Maksimum mesaj uzunlugu (karakter)
MAX_MESSAGE_LENGTH = 5000

# SQL injection pattern'leri
_SQL_PATTERNS = re.compile(
    r"(?i)"
    r"(?:(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\s+(?:FROM|INTO|TABLE|DATABASE|INDEX))"
    r"|(?:UNION\s+(?:ALL\s+)?SELECT)"
    r"|(?:;\s*(?:DROP|DELETE|TRUNCATE)\s)"
    r"|(?:--\s*$)"
    r"|(?:'\s*(?:OR|AND)\s+['\"]\s*['\"])"
    r"|(?:'\s*(?:OR|AND)\s+\d+\s*=\s*\d+)"
)

# Script injection pattern'leri
_SCRIPT_PATTERNS = re.compile(
    r"(?i)"
    r"(?:<\s*script[\s>])"
    r"|(?:javascript\s*:)"
    r"|(?:on(?:load|error|click|mouseover)\s*=)"
    r"|(?:<\s*iframe[\s>])"
)

# Prompt injection pattern'leri
_PROMPT_INJECTION_PATTERNS = re.compile(
    r"(?i)"
    r"(?:ignore\s+(?:all\s+)?(?:previous|above|prior)\s+instructions)"
    r"|(?:disregard\s+(?:all\s+)?(?:previous|above|prior))"
    r"|(?:you\s+are\s+now\s+(?:a|an)\s+)"
    r"|(?:new\s+instructions?\s*:)"
    r"|(?:system\s*:\s*you\s+are)"
    r"|(?:override\s+(?:system|safety)\s+(?:prompt|instructions?))"
    r"|(?:forget\s+(?:all\s+)?(?:your|previous)\s+(?:instructions?|rules?))"
)


async def check_input_guardrails(message: str) -> Tuple[bool, str]:
    """Kullanici mesajini guvenlik kontrollerinden gecir.

    Returns:
        (is_safe, reason) — True ise mesaj guvenli, False ise neden.
    """
    if not message or not message.strip():
        return True, ""

    # Uzunluk kontrolu
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Mesaj çok uzun ({len(message)} karakter). Maksimum {MAX_MESSAGE_LENGTH} karakter."

    # SQL injection kontrolu
    if _SQL_PATTERNS.search(message):
        return False, "Güvenlik kontrolü: mesajda potansiyel SQL injection tespit edildi."

    # Script injection kontrolu
    if _SCRIPT_PATTERNS.search(message):
        return False, "Güvenlik kontrolü: mesajda potansiyel script injection tespit edildi."

    # Prompt injection kontrolu
    if _PROMPT_INJECTION_PATTERNS.search(message):
        return False, "Güvenlik kontrolü: mesajda potansiyel prompt injection tespit edildi."

    return True, ""
