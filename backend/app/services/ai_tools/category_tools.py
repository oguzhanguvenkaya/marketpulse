"""Kategori analizi AI tool fonksiyonları.

Faz 2A: Hybrid search + reranker entegrasyonu.
ILIKE yerine hybrid_search_category + rerank_products kullanir.
"""

import logging
import re
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text

from app.core.logger import get_logger
from app.db.models import CategorySession, CategoryProduct
from app.services.query_normalizer import normalize_query, extract_brand
from app.services.embedding_service import build_search_text_category

logger = get_logger("ai.tools.category")

# Türkçe stop words — kelime analizi için filtrelenecek
_STOP_WORDS = {
    "ve", "ile", "bir", "bu", "da", "de", "için", "den", "dan", "ye", "ya",
    "mi", "mu", "mü", "ise", "olan", "gibi", "kadar", "en", "her", "daha",
    "çok", "az", "var", "yok", "ml", "lt", "mm", "cm", "gr", "kg", "adet",
    "the", "and", "for", "with", "from", "that", "this", "are", "was",
}


async def get_category_analysis(
    user_id: str, db: Session, category_name: str = "", platform: str = "",
    brand: str = "", seller: str = "", **kwargs
) -> dict:
    """Kategori ürünlerini analiz et — fiyat dağılımı, markalar, sponsorlu ürünler. Marka/satıcı filtresi destekler."""
    query = db.query(CategorySession).filter(
        CategorySession.user_id == user_id,
        db.query(CategoryProduct).filter(
            CategoryProduct.session_id == CategorySession.id
        ).exists(),
    )

    if category_name:
        query = query.filter(CategorySession.category_name.ilike(f"%{category_name}%"))
    if platform:
        query = query.filter(CategorySession.platform == platform)

    session = query.order_by(desc(CategorySession.created_at)).first()

    if not session:
        empty_session = db.query(CategorySession).filter(
            CategorySession.user_id == user_id,
            CategorySession.category_name.ilike(f"%{category_name}%") if category_name else True,
        ).first()
        if empty_session:
            return {"mesaj": f"'{category_name}' kategorisi taranmış ancak ürün verisi henüz yok. Category Explorer'dan tekrar tarama yapın."}
        return {"mesaj": f"'{category_name}' kategorisi için tarama verisi bulunamadı. Önce Category Explorer'dan tarama yapın."}

    product_query = db.query(CategoryProduct).filter(
        CategoryProduct.session_id == session.id,
    )

    # Marka filtresi — word_similarity fuzzy match ile
    if brand:
        normalized_brand = normalize_query(brand)
        brand_alias, _ = extract_brand(brand)
        if brand_alias:
            # Bilinen marka — exact match (case-insensitive)
            product_query = product_query.filter(
                func.lower(CategoryProduct.brand) == brand_alias.lower()
            )
        else:
            # Bilinmeyen marka — word_similarity fuzzy match
            product_query = product_query.filter(
                text("word_similarity(:brand, brand) > 0.3")
            ).params(brand=normalized_brand)
    # Satıcı filtresi
    if seller:
        product_query = product_query.filter(CategoryProduct.seller_name.ilike(f"%{seller}%"))

    products = product_query.order_by(CategoryProduct.position).all()

    if not products:
        filter_info = ""
        if brand:
            filter_info += f" marka='{brand}'"
        if seller:
            filter_info += f" satıcı='{seller}'"
        return {"mesaj": f"Bu kategori taramasında{filter_info} eşleşen ürün bulunamadı."}

    # Fiyat analizi
    prices = [float(p.price) for p in products if p.price]
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0

    # Marka dağılımı (ilk 10)
    brand_counts = {}
    for p in products:
        b = p.brand or "Bilinmiyor"
        brand_counts[b] = brand_counts.get(b, 0) + 1
    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Sponsorlu ürünler
    sponsored = [p for p in products if p.is_sponsored]

    # İndirimli ürünler
    discounted = [p for p in products if p.discount_percentage and p.discount_percentage > 0]

    # Satıcı dağılımı (ilk 10)
    seller_counts = {}
    for p in products:
        s = p.seller_name or "Bilinmiyor"
        seller_counts[s] = seller_counts.get(s, 0) + 1
    top_sellers = sorted(seller_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def _product_dict(p):
        return {
            "sira": p.position,
            "urun": p.name[:80] if p.name else "?",
            "marka": p.brand,
            "fiyat": float(p.price) if p.price else None,
            "indirim": f"%{p.discount_percentage:.0f}" if p.discount_percentage else None,
            "satici": p.seller_name,
            "puan": p.rating,
            "yorum": p.review_count,
            "sponsorlu": p.is_sponsored,
            "gorsel": p.image_url,
            "urun_url": p.url,
        }

    # Fiyata göre sıralı ürünler (en pahalı ve en ucuz)
    priced_products = sorted(
        [p for p in products if p.price],
        key=lambda p: float(p.price),
        reverse=True,
    )
    en_pahali = [_product_dict(p) for p in priced_products[:3]]
    en_ucuz = [_product_dict(p) for p in priced_products[-3:]]

    # Listeleme sırasına göre ilk 5
    ilk_5 = [_product_dict(p) for p in products[:5]]

    result = {
        "kategori": session.category_name,
        "platform": session.platform,
        "tarama_tarihi": session.created_at.isoformat(),
        "toplam_urun": len(products),
        "fiyat_analizi": {
            "ortalama": avg_price,
            "en_dusuk": min_price,
            "en_yuksek": max_price,
        },
        "en_pahali_3_urun": en_pahali,
        "en_ucuz_3_urun": en_ucuz,
        "marka_dagilimi": [{"marka": b, "urun_sayisi": c} for b, c in top_brands],
        "satici_dagilimi": [{"satici": s, "urun_sayisi": c} for s, c in top_sellers],
        "sponsorlu_urun_sayisi": len(sponsored),
        "indirimli_urun_sayisi": len(discounted),
        "listeleme_sirasi_ilk_5": ilk_5,
    }

    # Filtre bilgisini ekle
    if brand or seller:
        result["aktif_filtre"] = {}
        if brand:
            result["aktif_filtre"]["marka"] = brand
        if seller:
            result["aktif_filtre"]["satici"] = seller

    return result


async def get_product_descriptions(
    user_id: str, db: Session, product_name: str = "", category_name: str = "", **kwargs
) -> dict:
    """Kategori ürünlerinin açıklamalarını ve detaylarını getir. Hybrid search + reranker."""
    if not product_name and not category_name:
        return {"hata": "product_name veya category_name parametresi gerekli."}

    if product_name:
        # Hybrid search kullan
        from app.services.hybrid_search_service import hybrid_search_category
        from app.services.reranker_service import rerank_products

        normalized = normalize_query(product_name)
        products = await hybrid_search_category(
            db, user_id, normalized, category_name=category_name, limit=20
        )

        if products:
            products = await rerank_products(
                query=normalized,
                products=products,
                build_doc_fn=build_search_text_category,
                top_n=10,
            )
    else:
        # Sadece kategori adı ile — session bazlı arama
        session_query = db.query(CategorySession).filter(
            CategorySession.user_id == user_id,
        )
        if category_name:
            session_query = session_query.filter(
                CategorySession.category_name.ilike(f"%{category_name}%")
            )

        sessions = session_query.order_by(desc(CategorySession.created_at)).limit(5).all()
        if not sessions:
            return {"mesaj": "Kategori taraması bulunamadı."}

        session_ids = [s.id for s in sessions]
        products = db.query(CategoryProduct).filter(
            CategoryProduct.session_id.in_(session_ids),
        ).limit(10).all()

    if not products:
        return {"mesaj": f"'{product_name or category_name}' ile eşleşen ürün bulunamadı."}

    results = []
    for p in products:
        item = {
            "urun_adi": p.name[:100] if p.name else "?",
            "marka": p.brand,
            "fiyat": float(p.price) if p.price else None,
            "satici": p.seller_name,
            "aciklama": p.description[:1000] if p.description else None,
            "ozellikler": p.specs if p.specs else None,
            "urun_url": p.url,
        }
        results.append(item)

    return {
        "bulunan": len(results),
        "urunler": results,
    }


async def analyze_product_descriptions(
    user_id: str, db: Session, product_name: str = "", category_name: str = "", **kwargs
) -> dict:
    """Ürün açıklamalarındaki en çok geçen kelimeleri analiz et ve karşılaştır. Hybrid search + reranker."""
    if not product_name and not category_name:
        return {"hata": "product_name veya category_name parametresi gerekli."}

    if product_name:
        from app.services.hybrid_search_service import hybrid_search_category
        from app.services.reranker_service import rerank_products

        normalized = normalize_query(product_name)
        products = await hybrid_search_category(
            db, user_id, normalized, category_name=category_name, limit=20
        )

        if products:
            products = await rerank_products(
                query=normalized,
                products=products,
                build_doc_fn=build_search_text_category,
                top_n=10,
            )
    else:
        session_query = db.query(CategorySession).filter(
            CategorySession.user_id == user_id,
        )
        if category_name:
            session_query = session_query.filter(
                CategorySession.category_name.ilike(f"%{category_name}%")
            )

        sessions = session_query.order_by(desc(CategorySession.created_at)).limit(5).all()
        if not sessions:
            return {"mesaj": "Kategori taraması bulunamadı."}

        session_ids = [s.id for s in sessions]
        products = db.query(CategoryProduct).filter(
            CategoryProduct.session_id.in_(session_ids),
        ).limit(10).all()

    if not products:
        return {"mesaj": f"'{product_name or category_name}' ile eşleşen ürün bulunamadı."}

    # Her ürün için kelime analizi
    results = []
    for p in products:
        text = (p.description or "") + " " + (p.name or "")
        # Specs varsa JSON değerleri de ekle
        if p.specs and isinstance(p.specs, dict):
            text += " " + " ".join(str(v) for v in p.specs.values())

        words = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}", text.lower())
        filtered = [w for w in words if w not in _STOP_WORDS]
        word_freq = Counter(filtered).most_common(15)

        results.append({
            "urun_adi": p.name[:80] if p.name else "?",
            "aciklama_var": bool(p.description),
            "toplam_kelime": len(filtered),
            "en_cok_gecen_15": [{"kelime": w, "sayi": c} for w, c in word_freq],
        })

    # Ortak kelimeler (tüm ürünlerde geçen)
    if len(results) >= 2:
        all_word_sets = []
        for r in results:
            word_set = {item["kelime"] for item in r["en_cok_gecen_15"]}
            all_word_sets.append(word_set)
        common = set.intersection(*all_word_sets) if all_word_sets else set()
    else:
        common = set()

    return {
        "analiz_edilen_urun": len(results),
        "urunler": results,
        "ortak_kelimeler": list(common),
    }
