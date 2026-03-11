"""AI Tool Registry — OpenAI function calling tool tanımları ve dispatch."""

import logging
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from .price_tools import get_price_alerts, compare_seller_prices, get_product_insights
from .profitability_tools import calculate_profitability
from .search_tools import search_keyword_analysis, get_portfolio_summary, search_products_by_name
from .category_tools import get_category_analysis, get_product_descriptions, analyze_product_descriptions
from .action_tools import add_sku_to_monitor, add_competitor, set_price_alert, start_keyword_search
from .export_tools import export_data
from .analytics_tools import detect_price_anomalies, get_competitive_intel, suggest_campaign_price

logger = get_logger("ai.tools")

# OpenAI function calling format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_price_alerts",
            "description": "Kullanıcının aktif fiyat alarmlarını ve eşik ihlallerini gösterir. Fiyat düşüşü, eşik altına inme durumlarını kontrol eder.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_seller_prices",
            "description": "Belirli bir ürünün (SKU) tüm satıcılarının fiyatlarını karşılaştırır. Buybox sıralaması, kampanya fiyatları dahil.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Ürün SKU kodu",
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["hepsiburada", "trendyol"],
                        "description": "Platform adı",
                    },
                },
                "required": ["sku"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_insights",
            "description": "Ürünün fiyat geçmişini ve trendlerini gösterir. Son 7 günlük ortalama, min, max fiyat bilgisi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Ürün ID (UUID)",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_profitability",
            "description": "Ürün kârlılığını hesaplar. Komisyon, kargo ve maliyet düşüldükten sonra net kârı gösterir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["hepsiburada", "trendyol"],
                        "description": "Platform",
                    },
                    "category": {
                        "type": "string",
                        "description": "Ürün kategorisi (komisyon oranı için)",
                    },
                    "sale_price": {
                        "type": "number",
                        "description": "Satış fiyatı (TL)",
                    },
                    "unit_cost": {
                        "type": "number",
                        "description": "Birim maliyet (TL)",
                    },
                    "shipping_cost": {
                        "type": "number",
                        "description": "Kargo bedeli (TL)",
                    },
                },
                "required": ["platform", "sale_price", "unit_cost"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_keyword_analysis",
            "description": "Daha önce yapılmış keyword aramalarının sonuçlarını analiz eder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Aranacak keyword",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_summary",
            "description": "Kullanıcının izlediği ürünlerin genel özetini döndürür. Platform dağılımı, eşik tanımlı ürün sayısı vb.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_analysis",
            "description": "Kategori tarama verilerini analiz eder. Fiyat dağılımı, marka ve satıcı dağılımı, sponsorlu ürünler. Yazım hatası toleranslı marka filtresi destekler (örn: 'fraber' → 'Fra-Ber').",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_name": {
                        "type": "string",
                        "description": "Kategori adı veya kısmı (örn: 'Hızlı Cila', 'Oto Aksesuar')",
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["hepsiburada", "trendyol"],
                        "description": "Platform adı",
                    },
                    "brand": {
                        "type": "string",
                        "description": "Marka filtresi — yazım hatası toleranslı (örn: 'Sonax', 'fraber')",
                    },
                    "seller": {
                        "type": "string",
                        "description": "Satıcı filtresi (örn: 'Sonaxshop')",
                    },
                },
                "required": [],
            },
        },
    },
    # --- Product Description & Analysis ---
    {
        "type": "function",
        "function": {
            "name": "get_product_descriptions",
            "description": "Kategori taramasındaki ürünlerin açıklamalarını (description), özelliklerini (specs) getirir. Yazım hatası toleranslı, anlam bazlı arama. Ürün detaylarını görmek için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Ürün adı veya kelime (kısmi eşleşme)",
                    },
                    "category_name": {
                        "type": "string",
                        "description": "Kategori adı (opsiyonel, daraltmak için)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_product_descriptions",
            "description": "Ürün açıklamalarındaki en çok geçen kelimeleri analiz eder ve ürünler arası karşılaştırır. Yazım hatası toleranslı arama, kelime frekansı, ortak kelimeler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Ürün adı veya kelime (kısmi eşleşme)",
                    },
                    "category_name": {
                        "type": "string",
                        "description": "Kategori adı (opsiyonel)",
                    },
                },
                "required": [],
            },
        },
    },
    # --- Search by Name ---
    {
        "type": "function",
        "function": {
            "name": "search_products_by_name",
            "description": "İzlenen ürünler arasında ürün adına, markaya veya anahtar kelimeye göre arama yapar. Yazım hatası toleranslı, anlamsal benzerlik destekler (hybrid search). Ürün adı, SKU, fiyat ve buybox bilgisi döndürür.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Aranacak ürün adı veya kelime (kısmi eşleşme)",
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["hepsiburada", "trendyol"],
                        "description": "Platform filtresi (opsiyonel)",
                    },
                },
                "required": ["product_name"],
            },
        },
    },
    # --- Action Tools (yazma/değiştirme) ---
    {
        "type": "function",
        "function": {
            "name": "add_sku_to_monitor",
            "description": "Yeni bir SKU'yu fiyat izleme listesine ekler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "description": "Ürün SKU kodu"},
                    "platform": {"type": "string", "enum": ["hepsiburada", "trendyol", "amazon_tr", "n11"]},
                    "threshold_price": {"type": "number", "description": "Fiyat eşiği (TL)"},
                },
                "required": ["sku"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_competitor",
            "description": "Rakip satıcı ekler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seller_id": {"type": "string", "description": "Satıcı ID"},
                    "seller_name": {"type": "string", "description": "Satıcı adı"},
                    "platform": {"type": "string", "enum": ["hepsiburada", "trendyol"]},
                },
                "required": ["seller_id", "seller_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_price_alert",
            "description": "Ürün için fiyat eşiği alarm ayarlar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "description": "Ürün SKU kodu"},
                    "threshold_price": {"type": "number", "description": "Fiyat eşiği (TL)"},
                    "platform": {"type": "string", "enum": ["hepsiburada", "trendyol"]},
                },
                "required": ["sku", "threshold_price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_keyword_search",
            "description": "Keyword araması başlatır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Aranacak kelime"},
                    "platform": {"type": "string", "enum": ["hepsiburada", "trendyol"]},
                },
                "required": ["keyword"],
            },
        },
    },
    # --- Export Tools (dışa aktarım) ---
    {
        "type": "function",
        "function": {
            "name": "export_data",
            "description": "Kullanıcının verilerini dosya olarak dışa aktarır. JSON, CSV, Markdown veya TXT formatında indirme linki oluşturur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "enum": [
                            "monitored_products",
                            "category_products",
                            "seller_prices",
                            "search_results",
                        ],
                        "description": "Dışa aktarılacak veri türü",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "csv", "md", "txt"],
                        "description": "Dosya formatı",
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["hepsiburada", "trendyol"],
                        "description": "Platform filtresi (opsiyonel)",
                    },
                    "category_name": {
                        "type": "string",
                        "description": "Kategori adı (category_products için)",
                    },
                    "sku": {
                        "type": "string",
                        "description": "Ürün SKU kodu (seller_prices için)",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Arama kelimesi (search_results için)",
                    },
                },
                "required": ["data_type", "format"],
            },
        },
    },
    # --- Analytics Tools (analiz) ---
    {
        "type": "function",
        "function": {
            "name": "detect_price_anomalies",
            "description": "Son N gündeki anormal fiyat değişikliklerini tespit eder. Z-score > 2 olan fiyat hareketlerini listeler. Ani fiyat artışı/düşüşü tespiti için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Ürün SKU filtresi (opsiyonel, boş bırakılırsa tüm ürünler)",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Analiz süresi (gün, varsayılan: 7)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_competitive_intel",
            "description": "Rakip satıcılarla karşılaştırmalı analiz yapar. Buybox sıralaması, fiyat farkları, stok ve kargo durumu. Rekabet durumunu görmek için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Ürün SKU filtresi (opsiyonel)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_campaign_price",
            "description": "Hedef kâr marjına göre kampanya fiyat önerisi hesaplar. Komisyon, kargo ve maliyet dahil. Kampanya/indirim fiyatı planlamak için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Ürün SKU filtresi (opsiyonel)",
                    },
                    "target_margin": {
                        "type": "number",
                        "description": "Hedef kâr marjı (0.15 = %15, varsayılan: %15)",
                    },
                },
                "required": [],
            },
        },
    },
]

# Tool name → function mapping
_TOOL_MAP = {
    "get_price_alerts": get_price_alerts,
    "compare_seller_prices": compare_seller_prices,
    "get_product_insights": get_product_insights,
    "calculate_profitability": calculate_profitability,
    "search_keyword_analysis": search_keyword_analysis,
    "get_portfolio_summary": get_portfolio_summary,
    "get_category_analysis": get_category_analysis,
    "get_product_descriptions": get_product_descriptions,
    "analyze_product_descriptions": analyze_product_descriptions,
    "search_products_by_name": search_products_by_name,
    # Action tools
    "add_sku_to_monitor": add_sku_to_monitor,
    "add_competitor": add_competitor,
    "set_price_alert": set_price_alert,
    "start_keyword_search": start_keyword_search,
    # Export tools
    "export_data": export_data,
    # Analytics tools
    "detect_price_anomalies": detect_price_anomalies,
    "get_competitive_intel": get_competitive_intel,
    "suggest_campaign_price": suggest_campaign_price,
}


async def execute_tool(tool_name: str, arguments: dict, user_id: str, db: Session) -> dict:
    """Tool'u çalıştır ve sonucu döndür."""
    func = _TOOL_MAP.get(tool_name)
    if not func:
        return {"hata": f"Bilinmeyen tool: {tool_name}"}

    try:
        result = await func(user_id=user_id, db=db, **arguments)
        return result
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        # DB transaction hatasında session'ı rollback et,
        # yoksa sonraki tüm tool'lar da InFailedSqlTransaction ile çöker
        try:
            db.rollback()
        except Exception:
            pass
        return {"hata": f"Tool çalıştırma hatası: {str(e)}"}
