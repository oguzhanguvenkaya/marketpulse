#!/usr/bin/env python3
"""HB/TY Excel ürünlerini detay bilgileriyle zenginleştirme scripti.

Kullanim:
    cd backend
    python -m scripts.enrich_excel_products --hb ../hb_total.xlsx --ty ../ty_total.xlsx --output ../enriched_products.json
    python -m scripts.enrich_excel_products --hb ../hb_total.xlsx --output ../enriched_hb.json  # sadece HB
    python -m scripts.enrich_excel_products --hb ../hb_total.xlsx --ty ../ty_total.xlsx --output ../enriched.json --concurrency 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Path bootstrap
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.database import get_session_local  # noqa: E402
from app.db.models import MonitoredProduct  # noqa: E402
from app.services.hb_detail_scraper import (  # noqa: E402
    scrape_hb_product_detail,
    scrape_hb_listings_only,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Faz A: Excel Oku
# ---------------------------------------------------------------------------

def read_hb_excel(path: str) -> list[dict[str, Any]]:
    import pandas as pd
    df = pd.read_excel(path)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            'satici_stok_kodu': str(r.get('Satıcı Stok Kodu', '')).strip(),
            'sku': str(r.get('SKU', '')).strip(),
            'urun_adi': str(r.get('Ürün Adı', '')).strip(),
            'barkod': str(r.get('Barkod', '')).strip(),
            'marka': str(r.get('Marka', '')).strip(),
            'fiyat': r.get('Fiyat'),
            'stok': r.get('Stok'),
            'komisyon_orani': str(r.get('Komisyon Oranı', '')).strip(),
            'en_alt_kategori': str(r.get('En Alt Kategori', '')).strip(),
            'ana_kategori': str(r.get('Ana Kategori', '')).strip(),
            'en_temel_kategori': str(r.get('En Temel Kategori', '')).strip(),
            'durum': str(r.get('Durum', '')).strip(),
        })
    logger.info(f"HB Excel: {len(rows)} ürün okundu ({path})")
    return rows


def read_ty_excel(path: str) -> list[dict[str, Any]]:
    import pandas as pd
    df = pd.read_excel(path)
    rows = []
    for _, r in df.iterrows():
        gorseller = []
        for i in range(1, 9):
            col = f'Görsel {i}'
            val = r.get(col)
            if pd.notna(val) and str(val).strip():
                gorseller.append(str(val).strip())

        durum = r.get('Durum')
        durum_str = str(durum).strip() if pd.notna(durum) else ''

        rows.append({
            'barkod': str(r.get('Barkod', '')).strip(),
            'model_kodu': str(r.get('Model Kodu', '')).strip(),
            'tedarikci_stok_kodu': str(r.get('Tedarikçi Stok Kodu', '')).strip(),
            'urun_adi': str(r.get('Ürün Adı', '')).strip(),
            'urun_aciklamasi': str(r.get('Ürün Açıklaması', '')).strip() if pd.notna(r.get('Ürün Açıklaması')) else '',
            'piyasa_satis_fiyati': r.get('Piyasa Satış Fiyatı (KDV Dahil)'),
            'buybox_fiyati': r.get('BuyBox Fiyatı') if pd.notna(r.get('BuyBox Fiyatı')) else None,
            'stok': r.get('Ürün Stok Adedi'),
            'gorseller': gorseller,
            'gorsel_sayisi': len(gorseller),
            'kategori': str(r.get('Kategori İsmi', '')).strip(),
            'marka': str(r.get('Marka', '')).strip(),
            'komisyon_orani': r.get('Komisyon Oranı'),
            'durum': durum_str,
            'url': str(r.get('Trendyol.com Linki', '')).strip() if pd.notna(r.get('Trendyol.com Linki')) else '',
            'sevkiyat_suresi': r.get('Sevkiyat Süresi') if pd.notna(r.get('Sevkiyat Süresi')) else None,
            'sevkiyat_tipi': str(r.get('Sevkiyat Tipi', '')).strip() if pd.notna(r.get('Sevkiyat Tipi')) else '',
            'beden': str(r.get('Beden', '')).strip() if pd.notna(r.get('Beden')) else '',
        })
    logger.info(f"TY Excel: {len(rows)} ürün okundu ({path})")
    return rows


# ---------------------------------------------------------------------------
# Faz B: DB'den URL eşleştir
# ---------------------------------------------------------------------------

def match_hb_urls(hb_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """HB ürünlerini Price Monitor DB'deki URL'lerle eşleştir."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        products = db.query(
            MonitoredProduct.sku,
            MonitoredProduct.barcode,
            MonitoredProduct.product_url,
            MonitoredProduct.seller_stock_code,
        ).filter(
            MonitoredProduct.platform == 'hepsiburada',
        ).all()
    finally:
        db.close()

    sku_to_url: dict[str, str] = {}
    barcode_to_url: dict[str, str] = {}
    stock_code_to_url: dict[str, str] = {}

    for p in products:
        if p.product_url:
            if p.sku:
                sku_to_url[p.sku.strip()] = p.product_url.strip()
            if p.barcode:
                barcode_to_url[p.barcode.strip()] = p.product_url.strip()
            if p.seller_stock_code:
                stock_code_to_url[p.seller_stock_code.strip()] = p.product_url.strip()

    logger.info(f"DB'den {len(products)} HB ürün yüklendi (SKU: {len(sku_to_url)}, Barkod: {len(barcode_to_url)}, StokKodu: {len(stock_code_to_url)})")

    matched = []
    unmatched = []
    stats = {'sku': 0, 'barcode': 0, 'stock_code': 0, 'not_found': 0}

    for row in hb_rows:
        url = None
        match_field = 'not_found'

        # 1. SKU ile eşle
        if row['sku'] and row['sku'] in sku_to_url:
            url = sku_to_url[row['sku']]
            match_field = 'sku'
        # 2. Barkod ile eşle
        elif row['barkod'] and row['barkod'] in barcode_to_url:
            url = barcode_to_url[row['barkod']]
            match_field = 'barcode'
        # 3. Satıcı stok kodu ile eşle
        elif row['satici_stok_kodu'] and row['satici_stok_kodu'] in stock_code_to_url:
            url = stock_code_to_url[row['satici_stok_kodu']]
            match_field = 'stock_code'

        stats[match_field] += 1

        if url:
            matched.append({
                'excel_data': row,
                'url': url,
                'url_match_field': match_field,
            })
        else:
            unmatched.append({
                'sku': row['sku'],
                'barkod': row['barkod'],
                'satici_stok_kodu': row['satici_stok_kodu'],
                'urun_adi': row['urun_adi'],
                'reason': 'not_found_in_db',
            })

    logger.info(
        f"URL eşleştirme: {len(matched)} eşleşti, {len(unmatched)} bulunamadı | "
        f"SKU: {stats['sku']}, Barkod: {stats['barcode']}, StokKodu: {stats['stock_code']}"
    )
    return matched, unmatched


# ---------------------------------------------------------------------------
# Faz C: HB detay kazıma
# ---------------------------------------------------------------------------

async def scrape_hb_details(
    matched: list[dict],
    unmatched: list[dict],
    concurrency: int = 5,
) -> tuple[list[dict], list[dict]]:
    """Eşleşen HB ürünlerinin detaylarını kazı."""
    semaphore = asyncio.Semaphore(concurrency)
    total = len(matched)
    success_count = 0
    fail_count = 0

    async def _scrape_one(idx: int, item: dict) -> None:
        nonlocal success_count, fail_count
        sku = item['excel_data']['sku']
        url = item['url']

        async with semaphore:
            t0 = time.time()
            try:
                detail = await scrape_hb_product_detail(url, sku)
                elapsed = time.time() - t0
                if detail:
                    item['scraped_detail'] = detail
                    success_count += 1
                    logger.info(f"[{idx + 1}/{total}] SKU {sku} OK ({elapsed:.1f}s) — {detail.get('seller_count', 0)} satıcı, {len(detail.get('images', []))} görsel")
                else:
                    item['scraped_detail'] = None
                    fail_count += 1
                    logger.warning(f"[{idx + 1}/{total}] SKU {sku} BAŞARISIZ ({elapsed:.1f}s)")
            except Exception as e:
                elapsed = time.time() - t0
                item['scraped_detail'] = None
                fail_count += 1
                logger.error(f"[{idx + 1}/{total}] SKU {sku} HATA ({elapsed:.1f}s): {e}")

    # Paralel çalıştır
    tasks = [_scrape_one(i, item) for i, item in enumerate(matched)]
    await asyncio.gather(*tasks)

    logger.info(f"HB kazıma tamamlandı: {success_count} başarılı, {fail_count} başarısız / {total} toplam")

    # URL bulunamayan ürünler için sadece Listings API dene
    if unmatched:
        logger.info(f"URL eşleşmeyen {len(unmatched)} ürün için Listings API deneniyor...")
        listings_ok = 0
        for i, item in enumerate(unmatched):
            sku = item['sku']
            if not sku:
                continue
            async with semaphore:
                try:
                    detail = await scrape_hb_listings_only(sku)
                    if detail:
                        item['listings_data'] = detail
                        listings_ok += 1
                except Exception as e:
                    logger.debug(f"Listings-only hata {sku}: {e}")
        logger.info(f"Listings-only: {listings_ok}/{len(unmatched)} başarılı")

    return matched, unmatched


# ---------------------------------------------------------------------------
# Faz D+E: JSON oluştur ve yaz
# ---------------------------------------------------------------------------

def build_output(
    hb_matched: list[dict],
    hb_unmatched: list[dict],
    ty_rows: list[dict] | None,
) -> dict:
    """Final JSON yapısını oluştur."""
    hb_scraped_ok = sum(1 for m in hb_matched if m.get('scraped_detail'))

    output: dict[str, Any] = {
        'metadata': {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'hb_total': len(hb_matched) + len(hb_unmatched),
            'hb_matched': len(hb_matched),
            'hb_scraped_ok': hb_scraped_ok,
            'hb_scraped_failed': len(hb_matched) - hb_scraped_ok,
            'hb_unmatched': len(hb_unmatched),
            'ty_total': len(ty_rows) if ty_rows else 0,
        },
        'hb_products': hb_matched,
        'hb_unmatched': hb_unmatched,
    }

    if ty_rows is not None:
        output['ty_products'] = [{'excel_data': r} for r in ty_rows]

    return output


def write_json(data: dict, output_path: str) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    logger.info(f"JSON yazıldı: {output_path} ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    t_start = time.time()

    # Faz A: Excel oku
    hb_rows = read_hb_excel(args.hb) if args.hb else []
    ty_rows = read_ty_excel(args.ty) if args.ty else None

    if not hb_rows:
        logger.error("HB Excel dosyası belirtilmedi veya boş.")
        sys.exit(1)

    # Faz B: URL eşleştir
    hb_matched, hb_unmatched = match_hb_urls(hb_rows)

    # Faz C: HB detay kazı
    if not args.skip_scrape:
        hb_matched, hb_unmatched = await scrape_hb_details(
            hb_matched, hb_unmatched, concurrency=args.concurrency,
        )
    else:
        logger.info("--skip-scrape: Kazıma atlandı, sadece URL eşleştirme yapıldı.")

    # Faz D+E: JSON oluştur ve yaz
    output = build_output(hb_matched, hb_unmatched, ty_rows)
    write_json(output, args.output)

    elapsed = time.time() - t_start
    meta = output['metadata']
    logger.info(
        f"\nTamamlandı ({elapsed:.0f}s):\n"
        f"  HB: {meta['hb_matched']}/{meta['hb_total']} eşleşti, "
        f"{meta['hb_scraped_ok']} kazındı, {meta['hb_unmatched']} eşleşmedi\n"
        f"  TY: {meta['ty_total']} ürün (kazıma yok)\n"
        f"  Çıktı: {args.output}"
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HB/TY Excel ürün detay zenginleştirme')
    parser.add_argument('--hb', required=True, help='hb_total.xlsx dosya yolu')
    parser.add_argument('--ty', help='ty_total.xlsx dosya yolu (opsiyonel)')
    parser.add_argument('--output', '-o', default='../enriched_products.json', help='JSON çıktı yolu')
    parser.add_argument('--concurrency', '-c', type=int, default=5, help='Paralel kazıma sayısı (varsayılan: 5)')
    parser.add_argument('--skip-scrape', action='store_true', help='Kazıma atla, sadece URL eşleştir')
    args = parser.parse_args()
    asyncio.run(main(args))
