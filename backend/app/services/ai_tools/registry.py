"""AI Tool Registry — OpenAI function calling tool tanımları ve dispatch."""

import logging
from sqlalchemy.orm import Session

from .price_tools import get_price_alerts, compare_seller_prices, get_product_insights
from .profitability_tools import calculate_profitability
from .search_tools import search_keyword_analysis, get_portfolio_summary
from .action_tools import add_sku_to_monitor, add_competitor, set_price_alert, start_keyword_search

logger = logging.getLogger(__name__)

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
]

# Tool name → function mapping
_TOOL_MAP = {
    "get_price_alerts": get_price_alerts,
    "compare_seller_prices": compare_seller_prices,
    "get_product_insights": get_product_insights,
    "calculate_profitability": calculate_profitability,
    "search_keyword_analysis": search_keyword_analysis,
    "get_portfolio_summary": get_portfolio_summary,
    # Action tools
    "add_sku_to_monitor": add_sku_to_monitor,
    "add_competitor": add_competitor,
    "set_price_alert": set_price_alert,
    "start_keyword_search": start_keyword_search,
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
        return {"hata": f"Tool çalıştırma hatası: {str(e)}"}
