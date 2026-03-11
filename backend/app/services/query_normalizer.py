"""Query normalizer — marka alias, yazim normalizasyonu, marka cikarimi.

Chatbot query'lerini arama oncesi normalize eder:
- casefold + tire/bosluk normalizasyonu
- bilinen marka alias'lari ("fraber" → "Fra-Ber")
- marka + kalan kelime ayirimi ("sonax cila" → brand="Sonax", remainder="cila")
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# Bilinen marka alias'lari — casefold key ile
# LHS: kullanici yazabilecegi varyasyonlar
# RHS: veritabanindaki dogru marka adi
BRAND_ALIASES: dict[str, str] = {
    # Fra-Ber
    "fraber": "Fra-Ber",
    "fra ber": "Fra-Ber",
    "fra-ber": "Fra-Ber",
    "faber": "Fra-Ber",
    # Sonax
    "sonaks": "Sonax",
    "sonax": "Sonax",
    "snax": "Sonax",
    # Meguiar's
    "meguiars": "Meguiar's",
    "meguiar's": "Meguiar's",
    "meguiar": "Meguiar's",
    "meguairs": "Meguiar's",
    "meguars": "Meguiar's",
    # Soft99
    "soft99": "Soft99",
    "soft 99": "Soft99",
    # Turtle Wax
    "turtle wax": "Turtle Wax",
    "turtlewax": "Turtle Wax",
    "turtle": "Turtle Wax",
    # Koch Chemie
    "koch chemie": "Koch Chemie",
    "kochchemie": "Koch Chemie",
    "koch": "Koch Chemie",
    # Gyeon
    "gyeon": "Gyeon",
    "gyon": "Gyeon",
    # Auto Finesse
    "auto finesse": "Auto Finesse",
    "autofinesse": "Auto Finesse",
    # Chemical Guys
    "chemical guys": "Chemical Guys",
    "chemicalguys": "Chemical Guys",
    # Carpro
    "carpro": "CarPro",
    "car pro": "CarPro",
}

# Hizli lookup icin casefold edilmis → (alias_key_length, canonical_brand)
# Uzun match oncelikli olmasi icin uzunluga gore ters sirali
_ALIAS_LOOKUP: list[Tuple[str, str]] = sorted(
    [(k.casefold(), v) for k, v in BRAND_ALIASES.items()],
    key=lambda x: len(x[0]),
    reverse=True,
)


def _normalize_whitespace(text: str) -> str:
    """Coklu bosluk/tire'leri tek bosluga cevir."""
    return re.sub(r"[\s\-_]+", " ", text).strip()


def normalize_query(query: str) -> str:
    """Query'yi normalize et — casefold, bosluk temizligi, marka alias.

    Returns: Normalize edilmis query string.
    "fraber cila" → "Fra-Ber cila"
    "sonaks  wax" → "Sonax wax"
    """
    if not query:
        return ""

    normalized = _normalize_whitespace(query.strip())
    lower = normalized.casefold()

    # Marka alias kontrolu — en uzun match oncelikli
    for alias_key, canonical in _ALIAS_LOOKUP:
        if alias_key in lower:
            # Alias'i kanonik marka ile degistir (case-insensitive)
            pattern = re.compile(re.escape(alias_key), re.IGNORECASE)
            normalized = pattern.sub(canonical, normalized, count=1)
            break  # Sadece ilk match

    return normalized.strip()


def extract_brand(query: str) -> Tuple[Optional[str], str]:
    """Query'den marka adini cikart.

    Returns: (brand_name, remainder)
    "Fra-Ber cila" → ("Fra-Ber", "cila")
    "araba parlatma" → (None, "araba parlatma")
    """
    if not query:
        return None, ""

    normalized = normalize_query(query)
    lower = normalized.casefold()

    # Bilinen marka isimlerini kontrol et (kanonik degerler)
    canonical_brands = sorted(
        set(BRAND_ALIASES.values()),
        key=len,
        reverse=True,
    )

    for brand in canonical_brands:
        brand_lower = brand.casefold()
        if brand_lower in lower:
            # Markayi cikar, kalan kismi dondur
            pattern = re.compile(re.escape(brand), re.IGNORECASE)
            remainder = pattern.sub("", normalized, count=1).strip()
            remainder = _normalize_whitespace(remainder)
            return brand, remainder

    return None, normalized
