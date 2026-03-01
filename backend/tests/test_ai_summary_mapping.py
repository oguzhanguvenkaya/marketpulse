"""_extract_summary fonksiyonu icin unit testleri.

Plan dogrulama: Her tool icin Turkce key'lerin dogru okunup
summary string'inin uretildigi test edilir.
"""

import pytest
from app.services.ai_streaming_service import _extract_summary


class TestExtractSummary:
    """_extract_summary tool sonuclarindan dogru ozet uretmeli."""

    def test_get_price_alerts_summary(self):
        result = {
            "toplam_izlenen": 12,
            "esik_ihlali_sayisi": 3,
            "son_24_saat_alarm": 5,
            "ihlaller": [],
        }
        summary = _extract_summary(result, "get_price_alerts")
        assert "12" in summary
        assert "3" in summary

    def test_get_portfolio_summary(self):
        result = {
            "toplam_urun": 45,
            "platform_dagilimi": {"hepsiburada": 30, "trendyol": 15},
        }
        summary = _extract_summary(result, "get_portfolio_summary")
        assert "45" in summary

    def test_compare_seller_prices_summary(self):
        result = {
            "saticilar": [
                {"satici": "A", "fiyat": 100},
                {"satici": "B", "fiyat": 110},
                {"satici": "C", "fiyat": 120},
            ],
        }
        summary = _extract_summary(result, "compare_seller_prices")
        assert "3" in summary

    def test_compare_seller_prices_empty(self):
        result = {"saticilar": []}
        summary = _extract_summary(result, "compare_seller_prices")
        assert "0" in summary

    def test_calculate_profitability_summary(self):
        result = {
            "kar_marji_yuzde": 18.5,
            "net_kar": 55.0,
        }
        summary = _extract_summary(result, "calculate_profitability")
        assert "18.5" in summary

    def test_calculate_profitability_no_margin(self):
        result = {"net_kar": 0}
        summary = _extract_summary(result, "calculate_profitability")
        # kar_marji_yuzde yoksa fallback mesaj donmeli
        assert summary  # bos olmamali

    def test_get_product_insights_with_price(self):
        result = {
            "urun": "Test Urun",
            "guncel_fiyat": 299.90,
        }
        summary = _extract_summary(result, "get_product_insights")
        assert "Test Urun" in summary
        assert "299.9" in summary

    def test_get_product_insights_without_price(self):
        result = {
            "urun": "Test Urun",
            "veri_yok": True,
        }
        summary = _extract_summary(result, "get_product_insights")
        assert "Test Urun" in summary

    def test_search_keyword_analysis_summary(self):
        result = {
            "keyword": "cila",
            "toplam_arama": 5,
        }
        summary = _extract_summary(result, "search_keyword_analysis")
        assert "cila" in summary
        assert "5" in summary

    def test_get_category_analysis_summary(self):
        result = {
            "kategori": "Hizli Cila",
            "toplam_urun": 42,
        }
        summary = _extract_summary(result, "get_category_analysis")
        assert "42" in summary
        assert "Hizli Cila" in summary

    def test_get_category_analysis_empty(self):
        result = {"kategori": "", "toplam_urun": 0}
        summary = _extract_summary(result, "get_category_analysis")
        assert summary  # bos olmamali

    def test_get_product_descriptions_summary(self):
        result = {"bulunan": 8}
        summary = _extract_summary(result, "get_product_descriptions")
        assert "8" in summary

    def test_analyze_product_descriptions_summary(self):
        result = {
            "analiz_edilen_urun": 5,
            "ortak_kelimeler": ["cila", "parlatma", "koruma"],
        }
        summary = _extract_summary(result, "analyze_product_descriptions")
        assert "5" in summary
        assert "3" in summary

    def test_search_products_by_name_summary(self):
        result = {"bulunan": 3}
        summary = _extract_summary(result, "search_products_by_name")
        assert "3" in summary

    def test_export_data_success(self):
        result = {
            "basarili": True,
            "dosya_adi": "urunler_20260302.csv",
            "boyut": "12.5 KB",
        }
        summary = _extract_summary(result, "export_data")
        assert "urunler_20260302.csv" in summary
        assert "12.5 KB" in summary

    def test_export_data_failure(self):
        result = {"basarili": False}
        summary = _extract_summary(result, "export_data")
        assert "olusturulamadi" in summary.lower()

    def test_error_result(self):
        result = {"hata": "Urun bulunamadi"}
        summary = _extract_summary(result, "any_tool")
        assert "Hata" in summary
        assert "Urun bulunamadi" in summary

    def test_unknown_tool(self):
        result = {"some_key": "some_value"}
        summary = _extract_summary(result, "unknown_tool_xyz")
        assert summary == "Tamamlandi"

    def test_non_dict_result(self):
        summary = _extract_summary("string_result", "any_tool")
        assert summary == "Tamamlandi"
