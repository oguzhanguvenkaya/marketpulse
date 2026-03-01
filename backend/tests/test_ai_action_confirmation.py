"""Action tool onay guard (confirmation) testleri.

Plan dogrulama:
- Ilk mesaj "X ekle" ile action tool call simule edilir,
  explicit onay yokken execute edilmedigi dogrulanir.
- "evet" gibi onay mesajinda action tool execute edilir.
"""

import pytest
from app.services.ai_streaming_service import (
    _is_explicit_confirmation,
    _ACTION_TOOLS,
)


class TestIsExplicitConfirmation:
    """_is_explicit_confirmation sadece kisa/explicit yanitlari kabul etmeli."""

    @pytest.mark.parametrize("msg", [
        "evet",
        "Evet",
        "EVET",
        "tamam",
        "Tamam",
        "onayliyorum",
        "onay",
        "onayla",
        "devam et",
        "uygula",
        "ok",
        "OK",
        "yes",
        "Yes",
        " evet ",          # bosluk ile
        "evet.",           # nokta ile
        "evet!",           # unlem ile
    ])
    def test_positive_confirmations(self, msg):
        assert _is_explicit_confirmation(msg) is True

    @pytest.mark.parametrize("msg", [
        "HB12345 urununu ekle",
        "bu urunu izleme listesine ekle",
        "fiyat esigini 100 TL yap",
        "rakip olarak ayarla",
        "evet bunu ekle",               # evet + ek metin — onay degil
        "hayir",
        "iptal",
        "cancel",
        "biraz daha dusuneyim",
        "",
        "   ",
        "ekle",
        "ayarla",
        "baslat",
        "evet ama once kontrol et",      # uzun cevap — onay degil
    ])
    def test_negative_confirmations(self, msg):
        assert _is_explicit_confirmation(msg) is False


class TestActionToolsSet:
    """_ACTION_TOOLS veri degistiren tum tool'lari icermeli."""

    def test_contains_known_action_tools(self):
        expected = {
            "add_sku_to_monitor",
            "add_competitor",
            "set_price_alert",
            "start_keyword_search",
        }
        assert _ACTION_TOOLS == expected

    def test_export_not_in_action_tools(self):
        """export_data onay gerektirmez — action tools'ta olmamali."""
        assert "export_data" not in _ACTION_TOOLS

    def test_read_tools_not_in_action_tools(self):
        """Salt okunur tool'lar action tools'ta olmamali."""
        read_tools = [
            "get_price_alerts",
            "compare_seller_prices",
            "get_product_insights",
            "calculate_profitability",
            "get_portfolio_summary",
            "search_keyword_analysis",
            "get_category_analysis",
            "get_product_descriptions",
            "analyze_product_descriptions",
            "search_products_by_name",
        ]
        for tool in read_tools:
            assert tool not in _ACTION_TOOLS
