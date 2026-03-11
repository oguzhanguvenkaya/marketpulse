"""Query normalizer testleri.

Test edilen:
- Brand alias lookup (fraber → Fra-Ber)
- Casefold normalizasyonu
- Dash/space/underscore normalizasyonu
- extract_brand fonksiyonu
- Bilinmeyen marka passthrough
"""

import pytest
from app.services.query_normalizer import normalize_query, extract_brand


class TestNormalizeQuery:
    """normalize_query fonksiyonu testleri."""

    def test_brand_alias_fraber(self):
        """'fraber' → 'Fra-Ber' donusmeli."""
        assert normalize_query("fraber cila") == "Fra-Ber cila"

    def test_brand_alias_sonaks(self):
        """'sonaks' → 'Sonax' donusmeli."""
        assert normalize_query("sonaks wax") == "Sonax wax"

    def test_brand_alias_meguiars(self):
        """'meguairs' → 'Meguiar\\'s' donusmeli."""
        result = normalize_query("meguairs gold class")
        assert "Meguiar's" in result

    def test_casefold(self):
        """Buyuk/kucuk harf farki normalize edilmeli."""
        assert normalize_query("FRABER") == "Fra-Ber"

    def test_dash_space_normalize(self):
        """Coklu bosluk ve tire tek bosluga donusmeli."""
        result = normalize_query("fra  -  ber   cila")
        assert "Fra-Ber" in result

    def test_unknown_brand_passthrough(self):
        """Bilinmeyen marka oldugu gibi donmeli."""
        result = normalize_query("bilinmeyen marka urun")
        assert result == "bilinmeyen marka urun"

    def test_empty_query(self):
        """Bos query bos string donmeli."""
        assert normalize_query("") == ""
        assert normalize_query(None) == ""

    def test_only_whitespace(self):
        """Sadece bosluk bos string donmeli."""
        assert normalize_query("   ") == ""


class TestExtractBrand:
    """extract_brand fonksiyonu testleri."""

    def test_known_brand_extraction(self):
        """Bilinen marka cikarilmali."""
        brand, remainder = extract_brand("fraber cila")
        assert brand == "Fra-Ber"
        assert remainder == "cila"

    def test_known_brand_only(self):
        """Sadece marka ismi → kalan bos."""
        brand, remainder = extract_brand("sonax")
        assert brand == "Sonax"
        assert remainder == ""

    def test_unknown_brand(self):
        """Bilinmeyen marka → None donmeli."""
        brand, remainder = extract_brand("araba parlatma")
        assert brand is None
        assert remainder == "araba parlatma"

    def test_empty_query(self):
        """Bos query → None, bos string."""
        brand, remainder = extract_brand("")
        assert brand is None
        assert remainder == ""

    def test_brand_in_middle(self):
        """Marka kelime ortasinda da cikarilmali."""
        brand, remainder = extract_brand("en iyi sonax cila")
        assert brand == "Sonax"
        assert "cila" in remainder
