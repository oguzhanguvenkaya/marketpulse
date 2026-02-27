from __future__ import annotations

import uuid as uuid_mod
import logging
import asyncio
import re
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, BackgroundTasks, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from bs4 import BeautifulSoup

from app.db.database import get_db, SessionLocal
from app.db.models import CategorySession, CategoryProduct, User
from app.core.auth import get_current_user
from app.services.category_scraper_service import CategoryScraperService
from app.services.url_scraper_service import UrlScraperService
from app.services.price_monitor_service import PriceMonitorService

logger = logging.getLogger(__name__)

_active_fetches: dict[str, dict] = {}
_detail_semaphore = asyncio.Semaphore(10)

router = APIRouter(
    prefix="/api/category-explorer",
    tags=["Category Explorer"],
    dependencies=[Depends(get_current_user)],
)

scraper = CategoryScraperService()
url_scraper = UrlScraperService()


def _safe_numeric(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


class ScrapePageRequest(BaseModel):
    url: str
    session_id: Optional[str] = None
    page: int = 1
    page_count: int = 1


class FetchDetailRequest(BaseModel):
    product_ids: List[int]


class BulkFetchRequest(BaseModel):
    session_id: str
    product_ids: Optional[List[int]] = None


def _serialize_product(p: CategoryProduct) -> dict:
    return {
        'id': p.id,
        'session_id': str(p.session_id),
        'name': p.name,
        'url': p.url,
        'image_url': p.image_url,
        'brand': p.brand,
        'price': float(p.price) if p.price else None,
        'original_price': float(p.original_price) if p.original_price else None,
        'discount_percentage': p.discount_percentage,
        'rating': p.rating,
        'review_count': p.review_count,
        'is_sponsored': p.is_sponsored,
        'campaign_text': p.campaign_text,
        'seller_name': p.seller_name,
        'page_number': p.page_number,
        'position': p.position,
        'detail_fetched': p.detail_fetched,
        'detail_data': p.detail_data,
        'sku': p.sku,
        'barcode': p.barcode,
        'description': p.description,
        'specs': p.specs,
        'shipping_type': p.shipping_type,
        'stock_status': p.stock_status,
        'category_path': p.category_path,
        'seller_list': p.seller_list,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    }


def _serialize_session(s: CategorySession, include_products: bool = False) -> dict:
    result = {
        'id': str(s.id),
        'platform': s.platform,
        'category_url': s.category_url,
        'category_name': s.category_name,
        'breadcrumbs': s.breadcrumbs or [],
        'total_products': s.total_products,
        'pages_scraped': s.pages_scraped,
        'filter_data': s.filter_data,
        'status': s.status,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'product_count': len(s.category_products) if s.category_products else 0,
    }
    if include_products:
        result['products'] = [_serialize_product(p) for p in (s.category_products or [])]
    return result


@router.post("/scrape-page")
async def scrape_category_page(req: ScrapePageRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not req.url or not req.url.startswith('http'):
        raise HTTPException(400, "Valid URL required")

    platform = scraper.detect_platform(req.url)
    pages_to_scrape = max(1, min(req.page_count, 20))
    start_page = req.page

    session = None
    if req.session_id:
        try:
            session = db.query(CategorySession).filter(
                CategorySession.id == uuid_mod.UUID(req.session_id)
            ).first()
        except (ValueError, Exception):
            pass

    total_added = 0
    total_found = 0
    pages_scraped_list = []
    has_next = False

    existing_url_map: dict[str, CategoryProduct] = {}
    if session:
        existing = db.query(CategoryProduct).filter(
            CategoryProduct.session_id == session.id
        ).all()
        for ep in existing:
            if ep.url:
                clean_url = ep.url.split('?')[0] if ep.url else ''
                existing_url_map[clean_url] = ep

    total_updated = 0

    for page_num in range(start_page, start_page + pages_to_scrape):
        page_url = scraper.build_page_url(req.url, page_num)

        html = await scraper.fetch_page(page_url)
        if not html:
            if page_num == start_page:
                raise HTTPException(502, "Failed to fetch category page. The page may be protected or unavailable.")
            logger.warning(f"Failed to fetch page {page_num}, stopping multi-page scrape")
            break

        parsed = scraper.parse_category_page(html, page_url)

        if not session:
            session = CategorySession(
                platform=platform,
                category_url=req.url,
                category_name=parsed.get('category_name', ''),
                breadcrumbs=parsed.get('breadcrumbs', []),
                total_products=parsed.get('total_products', 0),
                filter_data=parsed.get('filter_data'),
                pages_scraped=0,
                status='active',
                user_id=user.id,
            )
            db.add(session)
            db.flush()
        else:
            if parsed.get('category_name') and page_num == start_page:
                session.category_name = parsed['category_name']
            if parsed.get('breadcrumbs') and page_num == start_page:
                session.breadcrumbs = parsed['breadcrumbs']
            if parsed.get('total_products') and page_num == start_page:
                session.total_products = parsed['total_products']
            if parsed.get('filter_data') and page_num == start_page:
                existing_fd = session.filter_data or {}
                new_fd = parsed['filter_data']
                merged = {
                    'brands': list(dict.fromkeys((existing_fd.get('brands', []) or []) + (new_fd.get('brands', []) or []))),
                    'sellers': list(dict.fromkeys((existing_fd.get('sellers', []) or []) + (new_fd.get('sellers', []) or []))),
                    'price_ranges': new_fd.get('price_ranges', existing_fd.get('price_ranges', [])),
                }
                session.filter_data = merged

        page_products = parsed.get('products', [])
        total_found += len(page_products)
        added = 0

        for idx, prod in enumerate(page_products):
            prod_url = prod.get('url', '')
            clean_prod_url = prod_url.split('?')[0] if prod_url else ''

            existing_product = existing_url_map.get(clean_prod_url) if clean_prod_url else None

            if existing_product:
                if _safe_numeric(prod.get('price')) is not None:
                    existing_product.price = _safe_numeric(prod.get('price'))
                if _safe_numeric(prod.get('original_price')) is not None:
                    existing_product.original_price = _safe_numeric(prod.get('original_price'))
                if prod.get('discount_percentage') is not None:
                    existing_product.discount_percentage = _safe_numeric(prod.get('discount_percentage'))
                if prod.get('rating') is not None:
                    existing_product.rating = _safe_numeric(prod.get('rating'))
                if prod.get('review_count') is not None:
                    existing_product.review_count = prod.get('review_count')
                if prod.get('image_url'):
                    existing_product.image_url = prod.get('image_url')
                if prod.get('campaign_text'):
                    existing_product.campaign_text = prod.get('campaign_text')
                existing_product.is_sponsored = prod.get('is_sponsored', False)
                existing_product.updated_at = datetime.utcnow()
                total_updated += 1
            else:
                cp = CategoryProduct(
                    session_id=session.id,
                    name=prod.get('name', ''),
                    url=prod_url,
                    image_url=prod.get('image_url', ''),
                    sku=prod.get('sku', ''),
                    price=_safe_numeric(prod.get('price')),
                    original_price=_safe_numeric(prod.get('original_price')),
                    discount_percentage=_safe_numeric(prod.get('discount_percentage')),
                    rating=_safe_numeric(prod.get('rating')),
                    review_count=prod.get('review_count'),
                    is_sponsored=prod.get('is_sponsored', False),
                    campaign_text=prod.get('campaign_text', ''),
                    page_number=page_num,
                    position=(page_num - 1) * 50 + idx + 1,
                )
                db.add(cp)
                existing_url_map[clean_prod_url] = cp
                added += 1

        total_added += added
        pages_scraped_list.append(page_num)
        session.pages_scraped = max(session.pages_scraped or 0, page_num)

        has_next = parsed.get('has_next_page', False)
        if not has_next and page_num < start_page + pages_to_scrape - 1:
            logger.info(f"No more pages after page {page_num}, stopping")
            break

        if len(page_products) == 0:
            logger.info(f"No products on page {page_num}, stopping")
            break

    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    all_products = db.query(CategoryProduct).filter(
        CategoryProduct.session_id == session.id
    ).order_by(CategoryProduct.position).all()

    return {
        'session': _serialize_session(session),
        'pages_scraped_list': pages_scraped_list,
        'page_scraped': pages_scraped_list[-1] if pages_scraped_list else start_page,
        'products_found': total_found,
        'products_added': total_added,
        'products_updated': total_updated,
        'has_next_page': has_next,
        'total_in_session': len(all_products),
        'products': [_serialize_product(p) for p in all_products],
        'breadcrumbs': parsed.get('breadcrumbs', []) if 'parsed' in locals() else [],
    }


@router.get("/sessions")
async def list_sessions(
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(CategorySession).filter(CategorySession.user_id == user.id).order_by(CategorySession.created_at.desc())
    if platform:
        q = q.filter(CategorySession.platform == platform)
    sessions = q.limit(limit).all()
    return {
        'sessions': [_serialize_session(s) for s in sessions]
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: Session = Depends(get_db)):
    try:
        session = db.query(CategorySession).filter(
            CategorySession.id == uuid_mod.UUID(session_id)
        ).first()
    except (ValueError, Exception):
        raise HTTPException(404, "Session not found")
    if not session:
        raise HTTPException(404, "Session not found")

    products = db.query(CategoryProduct).filter(
        CategoryProduct.session_id == session.id
    ).order_by(CategoryProduct.position).all()

    result = _serialize_session(session)
    result['products'] = [_serialize_product(p) for p in products]
    return result


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        session = db.query(CategorySession).filter(
            CategorySession.id == uuid_mod.UUID(session_id),
            CategorySession.user_id == user.id
        ).first()
    except (ValueError, Exception):
        raise HTTPException(404, "Session not found")
    if not session:
        raise HTTPException(404, "Session not found")

    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}


def _parse_utag_data(html: str) -> dict:
    utag = {}
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
    specs = {}
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
        desc_el = soup_partial.find('div', class_=re.compile(r'ProductDescription|productDescriptionContent', re.I))
        if desc_el:
            for tag in desc_el.find_all(['script', 'style']):
                tag.decompose()
            desc = desc_el.get_text(separator='\n', strip=True)[:5000]
    except Exception as e:
        logger.debug(f"Description parse error: {e}")
    return desc


async def _fetch_single_detail(product_id: int, semaphore: asyncio.Semaphore | None = None):
    sem = semaphore or _detail_semaphore
    async with sem:
        await _fetch_single_detail_inner(product_id)


async def _fetch_single_detail_inner(product_id: int):
    db = SessionLocal()
    try:
        product = db.query(CategoryProduct).filter(CategoryProduct.id == product_id).first()
        if not product or not product.url:
            return
        fetch_url = str(product.url)
        existing_sku = product.sku or ''
        platform = 'hepsiburada'
        session = db.query(CategorySession).filter(CategorySession.id == product.session_id).first()
        if session:
            platform = session.platform or 'hepsiburada'
    finally:
        db.close()

    if 'adservice' in fetch_url:
        redirect_match = re.search(r'redirect=([^&]+)', fetch_url)
        if redirect_match:
            from urllib.parse import unquote as _unquote
            fetch_url = _unquote(redirect_match.group(1)).split('?')[0]

    sku = existing_sku or CategoryScraperService._extract_sku_from_url(fetch_url)

    async def _do_html_fetch():
        try:
            return await url_scraper.fetch_url(fetch_url)
        except Exception as e:
            logger.error(f"HTML fetch error for product {product_id}: {e}")
            return None

    async def _do_listings_fetch(product_sku: str):
        if not product_sku or platform != 'hepsiburada':
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
        _do_listings_fetch(sku)
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
    specs = {}
    seller_list_data = []
    parsed = None

    if html_result:
        utag = _parse_utag_data(html_result)
        specs = _parse_hb_specs(html_result)
        description = _parse_hb_description(html_result)
        parsed = url_scraper.parse_html(html_result, fetch_url)

        brand = utag.get('product_brand', '') or (utag.get('product_brands', [''])[0] if utag.get('product_brands') else '')
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
        shipping_type = shipping_types[0] if isinstance(shipping_types, list) and shipping_types else str(shipping_types) if shipping_types else ''

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
        logger.warning(f"Both HTML and Listings API failed for product {product_id}")
        return

    if not listings_sellers and sku and platform == 'hepsiburada':
        logger.info(f"SKU {sku} discovered from HTML for product {product_id}, fetching Listings API")
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
        detail_data['title'] = utag.get('product_name_array', '') or (parsed.get('title') if parsed else '')
        detail_data['canonical_url'] = utag.get('canonical_url', '')
        detail_data['product_ids'] = utag.get('product_ids', [])

    db = SessionLocal()
    try:
        product = db.query(CategoryProduct).filter(CategoryProduct.id == product_id).first()
        if not product:
            return

        product.detail_fetched = True
        product.detail_data = detail_data
        if brand:
            product.brand = brand
        if seller_name:
            product.seller_name = seller_name
        if sku:
            product.sku = sku
        if barcode:
            product.barcode = barcode
        if description:
            product.description = description[:5000]
        if specs:
            product.specs = specs
        if shipping_type:
            product.shipping_type = shipping_type
        if stock_status:
            product.stock_status = stock_status
        if category_path:
            product.category_path = category_path
        if seller_list_data:
            product.seller_list = seller_list_data
        if rating_val:
            product.rating = rating_val
        if review_count_val:
            product.review_count = review_count_val
        if utag_price and utag_price > 0:
            product.price = utag_price

        if fetch_url != str(product.url):
            product.url = fetch_url

        product.updated_at = datetime.utcnow()
        db.commit()
        sellers_count = len(seller_list_data)
        logger.info(f"Detail fetched for product {product_id}: brand={brand}, sku={sku}, sellers={sellers_count}")
    except Exception as e:
        logger.error(f"Error saving detail for product {product_id}: {e}")
    finally:
        db.close()


async def _run_parallel_fetch(session_id: str, product_ids: list[int]):
    fetch_key = session_id
    _active_fetches[fetch_key] = {
        'product_ids': set(product_ids),
        'total': len(product_ids),
        'completed': 0,
        'failed': 0,
    }
    try:
        tasks = [_fetch_single_detail(pid) for pid in product_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                _active_fetches[fetch_key]['failed'] += 1
                logger.error(f"Detail fetch error: {r}")
            else:
                _active_fetches[fetch_key]['completed'] += 1
    except Exception as e:
        logger.error(f"Parallel fetch error: {e}")
    finally:
        _active_fetches.pop(fetch_key, None)


@router.post("/fetch-detail")
async def fetch_product_details(req: FetchDetailRequest, db: Session = Depends(get_db)):
    if not req.product_ids:
        raise HTTPException(400, "product_ids required")

    products = db.query(CategoryProduct).filter(
        CategoryProduct.id.in_(req.product_ids),
        CategoryProduct.detail_fetched == False,
    ).all()

    if not products:
        raise HTTPException(404, "No unfetched products found")

    product_ids = [p.id for p in products]
    session_id = str(products[0].session_id)

    asyncio.create_task(_run_parallel_fetch(session_id, product_ids))

    return {
        'message': f'Fetching details for {len(products)} products in parallel (10 concurrent)',
        'product_ids': product_ids,
        'total': len(product_ids),
    }


@router.post("/bulk-fetch")
async def bulk_fetch_details(req: BulkFetchRequest, db: Session = Depends(get_db)):
    try:
        session = db.query(CategorySession).filter(
            CategorySession.id == uuid_mod.UUID(req.session_id)
        ).first()
    except (ValueError, Exception):
        raise HTTPException(404, "Session not found")
    if not session:
        raise HTTPException(404, "Session not found")

    q = db.query(CategoryProduct).filter(
        CategoryProduct.session_id == session.id,
        CategoryProduct.detail_fetched == False,
    )

    if req.product_ids:
        q = q.filter(CategoryProduct.id.in_(req.product_ids))

    products = q.all()
    if not products:
        return {'message': 'No products to fetch', 'count': 0}

    product_ids = [p.id for p in products]

    asyncio.create_task(_run_parallel_fetch(str(session.id), product_ids))

    return {
        'message': f'Bulk fetching details for {len(products)} products in parallel (10 concurrent)',
        'count': len(products),
    }


@router.get("/products/{product_id}")
async def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    product = db.query(CategoryProduct).filter(CategoryProduct.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    return _serialize_product(product)


@router.delete("/products/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(CategoryProduct).filter(CategoryProduct.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    db.delete(product)
    db.commit()
    return {'message': 'Product deleted', 'id': product_id}


class BulkDeleteRequest(BaseModel):
    product_ids: List[int]


@router.post("/delete-products")
async def delete_products_bulk(req: BulkDeleteRequest, db: Session = Depends(get_db)):
    if not req.product_ids:
        raise HTTPException(400, "product_ids required")
    deleted = db.query(CategoryProduct).filter(
        CategoryProduct.id.in_(req.product_ids)
    ).delete(synchronize_session='fetch')
    db.commit()
    return {'message': f'{deleted} products deleted', 'deleted': deleted}


@router.get("/session-url-lookup")
async def session_url_lookup(
    category: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    if session_id:
        try:
            session = db.query(CategorySession).filter(CategorySession.id == uuid_mod.UUID(session_id)).first()
            if session:
                return {'category_url': session.category_url, 'session_id': str(session.id), 'category_name': session.category_name}
        except (ValueError, Exception):
            pass

    if not category:
        return {'category_url': None}

    base_q = db.query(CategorySession)
    if platform:
        base_q = base_q.filter(CategorySession.platform == platform)

    session = base_q.filter(CategorySession.category_name.ilike(f"%{category}%")).order_by(CategorySession.created_at.desc()).first()

    if not session:
        slug = category.lower().replace(' ', '-').replace('ı', 'i').replace('ö', 'o').replace('ü', 'u').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g')
        session = base_q.filter(CategorySession.category_url.ilike(f"%{slug}%")).order_by(CategorySession.created_at.desc()).first()

    if not session:
        parts = [p.strip() for p in category.replace(' > ', '>').replace(' / ', '>').split('>') if p.strip()]
        for part in reversed(parts):
            if len(part) < 3:
                continue
            session = base_q.filter(CategorySession.category_name.ilike(f"%{part}%")).order_by(CategorySession.created_at.desc()).first()
            if session:
                break

    if session:
        return {'category_url': session.category_url, 'session_id': str(session.id), 'category_name': session.category_name}
    return {'category_url': None}


@router.get("/category-filters")
async def get_category_filters(
    session_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    session_obj = None
    if session_id:
        try:
            session_obj = db.query(CategorySession).filter(CategorySession.id == uuid_mod.UUID(session_id)).first()
        except (ValueError, Exception):
            pass

    marketplace_fd = session_obj.filter_data if session_obj and session_obj.filter_data else None

    q = db.query(CategoryProduct).join(CategorySession, CategoryProduct.session_id == CategorySession.id)
    if platform:
        q = q.filter(CategorySession.platform == platform)
    if session_id:
        q = q.filter(CategoryProduct.session_id == session_id)
    elif category:
        leaf = category.split(' > ')[-1].strip() if ' > ' in category else category
        q = q.filter(CategorySession.category_name.ilike(f"%{leaf}%"))

    product_brands = [r[0] for r in q.with_entities(CategoryProduct.brand).filter(CategoryProduct.brand.isnot(None), CategoryProduct.brand != '').distinct().order_by(CategoryProduct.brand).all()]
    product_sellers = [r[0] for r in q.with_entities(CategoryProduct.seller_name).filter(CategoryProduct.seller_name.isnot(None), CategoryProduct.seller_name != '').distinct().order_by(CategoryProduct.seller_name).all()]

    if marketplace_fd:
        mp_brands = marketplace_fd.get('brands', []) or []
        mp_sellers = marketplace_fd.get('sellers', []) or []
        all_brands = list(dict.fromkeys(mp_brands + product_brands))
        all_sellers = list(dict.fromkeys(mp_sellers + product_sellers))
    else:
        all_brands = product_brands
        all_sellers = product_sellers

    price_row = q.with_entities(
        func.min(CategoryProduct.price),
        func.max(CategoryProduct.price),
    ).first()

    mp_price_ranges = marketplace_fd.get('price_ranges', []) if marketplace_fd else []

    return {
        'brands': sorted(all_brands, key=str.lower),
        'sellers': sorted(all_sellers, key=str.lower),
        'price_range': {
            'min': float(price_row[0]) if price_row and price_row[0] else 0,
            'max': float(price_row[1]) if price_row and price_row[1] else 0,
        },
        'marketplace_price_ranges': mp_price_ranges,
        'marketplace_filter_count': {
            'brands': len(marketplace_fd.get('brands', [])) if marketplace_fd else 0,
            'sellers': len(marketplace_fd.get('sellers', [])) if marketplace_fd else 0,
        },
    }


@router.get("/products-by-category")
async def list_products_by_category(
    category: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    seller: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    is_sponsored: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: Optional[str] = Query('asc'),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    q = db.query(CategoryProduct).join(CategorySession, CategoryProduct.session_id == CategorySession.id)

    if platform:
        q = q.filter(CategorySession.platform == platform)
    if session_id:
        q = q.filter(CategoryProduct.session_id == session_id)
    elif category:
        leaf = category.split(' > ')[-1].strip() if ' > ' in category else category
        q = q.filter(CategorySession.category_name.ilike(f"%{leaf}%"))
    if search:
        q = q.filter(or_(
            CategoryProduct.name.ilike(f"%{search}%"),
            CategoryProduct.brand.ilike(f"%{search}%"),
            CategoryProduct.seller_name.ilike(f"%{search}%"),
        ))
    if brand:
        q = q.filter(CategoryProduct.brand == brand)
    if seller:
        q = q.filter(CategoryProduct.seller_name == seller)
    if min_price is not None:
        q = q.filter(CategoryProduct.price >= min_price)
    if max_price is not None:
        q = q.filter(CategoryProduct.price <= max_price)
    if min_rating is not None:
        q = q.filter(CategoryProduct.rating >= min_rating)
    if is_sponsored is not None:
        q = q.filter(CategoryProduct.is_sponsored == is_sponsored)

    total = q.count()

    stats_row = q.with_entities(
        func.avg(CategoryProduct.price),
        func.count(func.distinct(func.nullif(CategoryProduct.brand, ''))),
        func.count(func.distinct(func.nullif(CategoryProduct.seller_name, ''))),
    ).first()

    last_scraped_row = q.with_entities(func.max(CategoryProduct.created_at)).first()

    sort_col_map = {
        'price': CategoryProduct.price,
        'name': CategoryProduct.name,
        'rating': CategoryProduct.rating,
        'position': CategoryProduct.position,
        'created_at': CategoryProduct.created_at,
    }
    sort_column = sort_col_map.get(sort_by, CategoryProduct.position)
    if sort_dir == 'desc':
        q = q.order_by(sort_column.desc().nullslast())
    else:
        q = q.order_by(sort_column.asc().nullsfirst())

    offset = (page - 1) * page_size
    products = q.offset(offset).limit(page_size).all()

    sessions_q = db.query(CategorySession)
    if platform:
        sessions_q = sessions_q.filter(CategorySession.platform == platform)
    if session_id:
        sessions_q = sessions_q.filter(CategorySession.id == session_id)
    related_sessions = sessions_q.order_by(CategorySession.created_at.desc()).limit(20).all()

    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size if total > 0 else 0,
        'products': [_serialize_product(p) for p in products],
        'filtered_stats': {
            'avg_price': float(stats_row[0]) if stats_row[0] else 0,
            'brand_count': stats_row[1] or 0,
            'seller_count': stats_row[2] or 0,
            'last_scraped': last_scraped_row[0].isoformat() if last_scraped_row and last_scraped_row[0] else None,
        },
        'sessions': [_serialize_session(s) for s in related_sessions],
    }


@router.get("/fetch-status/{session_id}")
async def fetch_status(session_id: str, db: Session = Depends(get_db)):
    try:
        session = db.query(CategorySession).filter(
            CategorySession.id == uuid_mod.UUID(session_id)
        ).first()
    except (ValueError, Exception):
        raise HTTPException(404, "Session not found")
    if not session:
        raise HTTPException(404, "Session not found")

    active = _active_fetches.get(session_id)

    if active:
        submitted_ids = active['product_ids']
        submitted_total = active['total']
        fetched_of_submitted = db.query(func.count(CategoryProduct.id)).filter(
            CategoryProduct.id.in_(submitted_ids),
            CategoryProduct.detail_fetched == True,
        ).scalar()
        return {
            'session_id': session_id,
            'total_products': submitted_total,
            'detail_fetched': fetched_of_submitted,
            'pending': submitted_total - fetched_of_submitted,
            'is_running': True,
        }

    total = db.query(func.count(CategoryProduct.id)).filter(
        CategoryProduct.session_id == session.id
    ).scalar()

    fetched = db.query(func.count(CategoryProduct.id)).filter(
        CategoryProduct.session_id == session.id,
        CategoryProduct.detail_fetched == True,
    ).scalar()

    return {
        'session_id': str(session.id),
        'total_products': total,
        'detail_fetched': fetched,
        'pending': total - fetched,
        'is_running': False,
    }
