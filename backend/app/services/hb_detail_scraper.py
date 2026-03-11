"""HB ürün detay sayfası kazıma servisi (DB bağımsız).

category_explorer_routes.py'deki _fetch_single_detail_inner mantığının
yeniden kullanılabilir, DB'ye bağımlı olmayan versiyonu.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from app.services.url_scraper_service import UrlScraperService
from app.services.price_monitor_service import PriceMonitorService

logger = logging.getLogger(__name__)

url_scraper = UrlScraperService()


# ---------------------------------------------------------------------------
# Helper parsers (pure functions — category_explorer_routes.py'den kopyalandı)
# ---------------------------------------------------------------------------

def _parse_utag_data(html: str) -> dict:
    utag: dict = {}
    try:
        idx = html.find('utagData')
        if idx == -1:
            return utag
        brace_start = html.find('{', idx)
        if brace_start == -1:
            return utag
        depth = 0
        end = brace_start
        for i in range(brace_start, min(brace_start + 30000, len(html))):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
            if depth == 0:
                end = i + 1
                break
        if depth != 0:
            return utag
        raw = html[brace_start:end]
        cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', raw)
        utag = json.loads(cleaned)
    except (json.JSONDecodeError, Exception) as e:
        logger.debug(f"utagData parse error: {e}")
    return utag


def _parse_hb_specs(html: str) -> dict:
    specs: dict = {}
    try:
        soup_partial = BeautifulSoup(html, 'html.parser')
        specs_container = soup_partial.find('div', attrs={'data-test-id': 'KeyFeaturesTable'})
        if not specs_container:
            specs_container = soup_partial.find('div', id='techSpecs')
        if specs_container:
            rows = specs_container.find_all('div', class_=re.compile(r'jkj4C4|spec-row', re.I))
            if not rows:
                rows = specs_container.find_all('li')
            for row in rows:
                children = row.find_all('div', recursive=False)
                if len(children) >= 2:
                    key = children[0].get_text(strip=True)
                    val = children[1].get_text(strip=True)
                    if key:
                        specs[key] = val
                else:
                    spans = row.find_all('span')
                    if len(spans) >= 2:
                        specs[spans[0].get_text(strip=True)] = spans[1].get_text(strip=True)
    except Exception as e:
        logger.debug(f"Specs parse error: {e}")
    return specs


def _parse_hb_description(html: str) -> str:
    desc = ''
    try:
        soup_partial = BeautifulSoup(html, 'html.parser')
        desc_el = soup_partial.find(
            'div',
            class_=re.compile(r'ProductDescription|productDescriptionContent', re.I),
        )
        if desc_el:
            for tag in desc_el.find_all(['script', 'style']):
                tag.decompose()
            desc = desc_el.get_text(separator='\n', strip=True)[:5000]
    except Exception as e:
        logger.debug(f"Description parse error: {e}")
    return desc


def _extract_sku_from_url(url: str) -> str:
    m = re.search(r'-pm-([A-Za-z0-9]+)(?:\?|$|/)', url)
    if m:
        return m.group(1)
    m2 = re.search(r'/([A-Z]{2,4}\d{8,}[A-Z0-9]*)(?:\?|$|/)', url)
    if m2:
        return m2.group(1)
    return ''


# ---------------------------------------------------------------------------
# Ana kazıma fonksiyonu
# ---------------------------------------------------------------------------

async def scrape_hb_product_detail(
    url: str,
    sku: str = '',
) -> dict[str, Any] | None:
    """HB ürün detay sayfasını kazı ve structured dict döndür.

    Args:
        url: Tam HB ürün URL'i
        sku: Opsiyonel HB SKU (yoksa URL'den çıkarılır)

    Returns:
        detail_data dict veya hata durumunda None
    """
    fetch_url = url

    # adservice redirect çöz
    if 'adservice' in fetch_url:
        redirect_match = re.search(r'redirect=([^&]+)', fetch_url)
        if redirect_match:
            from urllib.parse import unquote
            fetch_url = unquote(redirect_match.group(1)).split('?')[0]

    if not sku:
        sku = _extract_sku_from_url(fetch_url)

    # HTML + Listings API paralel çek
    async def _do_html_fetch():
        try:
            return await url_scraper.fetch_url(fetch_url)
        except Exception as e:
            logger.error(f"HTML fetch error for {sku}: {e}")
            return None

    async def _do_listings_fetch(product_sku: str):
        if not product_sku:
            return None
        try:
            pm = PriceMonitorService()
            result = await pm.fetch_listings(product_sku)
            if result.get('success') and result.get('data'):
                return pm.parse_listings(result['data'])
            return None
        except Exception as e:
            logger.error(f"Listings API error for {product_sku}: {e}")
            return None

    html_result, listings_sellers = await asyncio.gather(
        _do_html_fetch(),
        _do_listings_fetch(sku),
    )

    brand = ''
    seller_name = ''
    barcode = ''
    category_path = ''
    stock_status = ''
    shipping_type = ''
    rating_val = None
    review_count_val = None
    utag_price = None
    description = ''
    specs: dict = {}
    seller_list_data: list = []
    parsed = None

    if html_result:
        utag = _parse_utag_data(html_result)
        specs = _parse_hb_specs(html_result)
        description = _parse_hb_description(html_result)
        parsed = url_scraper.parse_html(html_result, fetch_url)

        brand = utag.get('product_brand', '') or (
            utag.get('product_brands', [''])[0] if utag.get('product_brands') else ''
        )
        if not brand and parsed:
            brand = parsed.get('brand', '')

        if not sku:
            product_skus = utag.get('product_skus', [])
            sku = product_skus[0] if product_skus else ''
            if not sku and parsed:
                sku = parsed.get('sku', '')

        barcodes = utag.get('product_barcodes', [])
        barcode = barcodes[0] if barcodes else utag.get('product_barcode', '')
        if not barcode and parsed:
            barcode = parsed.get('barcode', '')

        category_path = utag.get('category_name_hierarchy', '')
        if not category_path and parsed:
            cats = parsed.get('category_breadcrumbs', [])
            if isinstance(cats, list):
                names = [c.get('name', '') if isinstance(c, dict) else str(c) for c in cats]
                category_path = ' > '.join(n for n in names if n)

        stock_status = utag.get('product_status', '')
        if not stock_status and parsed:
            stock_status = parsed.get('availability', '')

        shipping_types = utag.get('shipping_type', [])
        shipping_type = (
            shipping_types[0]
            if isinstance(shipping_types, list) and shipping_types
            else str(shipping_types) if shipping_types else ''
        )

        review_rate = utag.get('review_rate', '')
        if review_rate:
            try:
                rating_val = float(str(review_rate).replace(',', '.'))
            except (ValueError, TypeError):
                pass
        rc = utag.get('review_count', '')
        if rc:
            try:
                review_count_val = int(str(rc).replace('.', ''))
            except (ValueError, TypeError):
                pass

        prices = utag.get('product_prices', [])
        if prices:
            try:
                utag_price = float(str(prices[0]).replace(',', ''))
            except (ValueError, TypeError):
                pass

        if not specs and parsed:
            specs = parsed.get('product_specs', {}) or {}
    elif not listings_sellers:
        logger.warning(f"Both HTML and Listings API failed for SKU {sku}")
        return None

    # HTML'den SKU bulundu ama Listings başarısızsa tekrar dene
    if not listings_sellers and sku:
        try:
            pm = PriceMonitorService()
            result = await pm.fetch_listings(sku)
            if result.get('success') and result.get('data'):
                listings_sellers = pm.parse_listings(result['data'])
        except Exception as e:
            logger.error(f"Deferred Listings API error for {sku}: {e}")

    if listings_sellers:
        seller_list_data = listings_sellers
        buybox = next((s for s in listings_sellers if s.get('buybox_order') == 1), None)
        if not buybox and listings_sellers:
            buybox = listings_sellers[0]
        if buybox:
            if not seller_name:
                seller_name = buybox.get('merchant_name', '')
            listings_price = buybox.get('price')
            if listings_price:
                utag_price = listings_price
    else:
        if html_result:
            utag = _parse_utag_data(html_result)
            merchant_names = utag.get('merchant_names', [])
            seller_name = merchant_names[0] if merchant_names else ''
            if not seller_name:
                seller_name = utag.get('order_store', '')
            if not seller_name and parsed:
                seller_name = parsed.get('seller_name', '')

    detail_data = {
        'title': '',
        'description': description or (parsed.get('description', '') if parsed else ''),
        'price': utag_price or (parsed.get('price') if parsed else None),
        'currency': 'TRY',
        'brand': brand,
        'sku': sku,
        'barcode': barcode,
        'availability': stock_status,
        'rating': rating_val or (parsed.get('rating') if parsed else None),
        'review_count': review_count_val or (parsed.get('review_count') if parsed else None),
        'seller_name': seller_name,
        'seller_list': seller_list_data,
        'seller_count': len(seller_list_data),
        'category': category_path,
        'category_breadcrumbs': parsed.get('category_breadcrumbs') if parsed else [],
        'images': parsed.get('images') if parsed else [],
        'product_specs': specs,
        'shipping_type': shipping_type,
        'shipping_info': parsed.get('shipping_info') if parsed else None,
        'return_policy': parsed.get('return_policy') if parsed else None,
    }

    if html_result:
        utag = _parse_utag_data(html_result)
        detail_data['title'] = utag.get('product_name_array', '') or (
            parsed.get('title') if parsed else ''
        )
        detail_data['canonical_url'] = utag.get('canonical_url', '')
        detail_data['product_ids'] = utag.get('product_ids', [])

    return detail_data


async def scrape_hb_listings_only(sku: str) -> dict[str, Any] | None:
    """Sadece Listings API ile seller verisi çek (URL olmayan ürünler için)."""
    try:
        pm = PriceMonitorService()
        result = await pm.fetch_listings(sku)
        if result.get('success') and result.get('data'):
            sellers = pm.parse_listings(result['data'])
            if sellers:
                buybox = next((s for s in sellers if s.get('buybox_order') == 1), None)
                if not buybox:
                    buybox = sellers[0]
                return {
                    'title': '',
                    'description': '',
                    'price': buybox.get('price') if buybox else None,
                    'currency': 'TRY',
                    'brand': '',
                    'sku': sku,
                    'barcode': '',
                    'availability': '',
                    'rating': None,
                    'review_count': None,
                    'seller_name': buybox.get('merchant_name', '') if buybox else '',
                    'seller_list': sellers,
                    'seller_count': len(sellers),
                    'category': '',
                    'category_breadcrumbs': [],
                    'images': [],
                    'product_specs': {},
                    'shipping_type': '',
                    'shipping_info': None,
                    'return_policy': None,
                }
    except Exception as e:
        logger.error(f"Listings-only fetch error for {sku}: {e}")
    return None
