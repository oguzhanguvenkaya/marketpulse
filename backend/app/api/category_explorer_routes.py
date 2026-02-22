import uuid as uuid_mod
import logging
import asyncio
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, BackgroundTasks, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel

from app.db.database import get_db, SessionLocal
from app.db.models import CategorySession, CategoryProduct
from app.core.security import require_mutating_api_key
from app.services.category_scraper_service import CategoryScraperService
from app.services.url_scraper_service import UrlScraperService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/category-explorer",
    tags=["Category Explorer"],
    dependencies=[Depends(require_mutating_api_key)],
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
        'status': s.status,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'product_count': len(s.category_products) if s.category_products else 0,
    }
    if include_products:
        result['products'] = [_serialize_product(p) for p in (s.category_products or [])]
    return result


@router.post("/scrape-page")
async def scrape_category_page(req: ScrapePageRequest, db: Session = Depends(get_db)):
    if not req.url or not req.url.startswith('http'):
        raise HTTPException(400, "Valid URL required")

    platform = scraper.detect_platform(req.url)
    page_url = scraper.build_page_url(req.url, req.page)

    html = await scraper.fetch_page(page_url)
    if not html:
        raise HTTPException(502, "Failed to fetch category page. The page may be protected or unavailable.")

    parsed = scraper.parse_category_page(html, page_url)

    session = None
    if req.session_id:
        try:
            session = db.query(CategorySession).filter(
                CategorySession.id == uuid_mod.UUID(req.session_id)
            ).first()
        except (ValueError, Exception):
            pass

    if not session:
        session = CategorySession(
            platform=platform,
            category_url=req.url,
            category_name=parsed.get('category_name', ''),
            breadcrumbs=parsed.get('breadcrumbs', []),
            total_products=parsed.get('total_products', 0),
            pages_scraped=0,
            status='active',
        )
        db.add(session)
        db.flush()
    else:
        if parsed.get('category_name'):
            session.category_name = parsed['category_name']
        if parsed.get('breadcrumbs'):
            session.breadcrumbs = parsed['breadcrumbs']
        if parsed.get('total_products'):
            session.total_products = parsed['total_products']

    existing_urls = set()
    if req.page > 1:
        existing = db.query(CategoryProduct.url).filter(
            CategoryProduct.session_id == session.id
        ).all()
        existing_urls = {r[0] for r in existing if r[0]}

    added = 0
    for idx, prod in enumerate(parsed.get('products', [])):
        if prod.get('url') and prod['url'] in existing_urls:
            continue

        cp = CategoryProduct(
            session_id=session.id,
            name=prod.get('name', ''),
            url=prod.get('url', ''),
            image_url=prod.get('image_url', ''),
            brand=prod.get('brand', ''),
            price=_safe_numeric(prod.get('price')),
            original_price=_safe_numeric(prod.get('original_price')),
            discount_percentage=_safe_numeric(prod.get('discount_percentage')),
            rating=_safe_numeric(prod.get('rating')),
            review_count=prod.get('review_count'),
            is_sponsored=prod.get('is_sponsored', False),
            campaign_text=prod.get('campaign_text', ''),
            seller_name=prod.get('seller_name', ''),
            page_number=req.page,
            position=(req.page - 1) * 50 + idx + 1,
        )
        db.add(cp)
        added += 1

    session.pages_scraped = max(session.pages_scraped or 0, req.page)
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    all_products = db.query(CategoryProduct).filter(
        CategoryProduct.session_id == session.id
    ).order_by(CategoryProduct.position).all()

    return {
        'session': _serialize_session(session),
        'page_scraped': req.page,
        'products_found': len(parsed.get('products', [])),
        'products_added': added,
        'has_next_page': parsed.get('has_next_page', False),
        'total_in_session': len(all_products),
        'products': [_serialize_product(p) for p in all_products],
        'breadcrumbs': parsed.get('breadcrumbs', []),
    }


@router.get("/sessions")
async def list_sessions(
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(CategorySession).order_by(CategorySession.created_at.desc())
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
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    try:
        session = db.query(CategorySession).filter(
            CategorySession.id == uuid_mod.UUID(session_id)
        ).first()
    except (ValueError, Exception):
        raise HTTPException(404, "Session not found")
    if not session:
        raise HTTPException(404, "Session not found")

    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}


async def _fetch_single_detail(product_id: int):
    db = SessionLocal()
    try:
        product = db.query(CategoryProduct).filter(CategoryProduct.id == product_id).first()
        if not product or not product.url:
            return

        html = await url_scraper.fetch_url(product.url)
        if not html:
            logger.warning(f"Failed to fetch detail for product {product_id}: {product.url[:80]}")
            return

        parsed = url_scraper.parse_html(html, product.url)
        if parsed:
            detail_data = {
                'title': parsed.get('title'),
                'description': parsed.get('description'),
                'price': parsed.get('price'),
                'currency': parsed.get('currency'),
                'brand': parsed.get('brand'),
                'sku': parsed.get('sku'),
                'barcode': parsed.get('barcode'),
                'availability': parsed.get('availability'),
                'rating': parsed.get('rating'),
                'rating_count': parsed.get('rating_count'),
                'review_count': parsed.get('review_count'),
                'reviews': parsed.get('reviews'),
                'seller_name': parsed.get('seller_name'),
                'category': parsed.get('category'),
                'category_breadcrumbs': parsed.get('category_breadcrumbs'),
                'images': parsed.get('images'),
                'product_specs': parsed.get('product_specs'),
                'shipping_info': parsed.get('shipping_info'),
                'return_policy': parsed.get('return_policy'),
            }
            product.detail_fetched = True
            product.detail_data = detail_data
            db.commit()
            logger.info(f"Detail fetched for product {product_id}: {product.name[:50] if product.name else 'N/A'}")
    except Exception as e:
        logger.error(f"Error fetching detail for product {product_id}: {e}")
    finally:
        db.close()


@router.post("/fetch-detail")
async def fetch_product_details(req: FetchDetailRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not req.product_ids:
        raise HTTPException(400, "product_ids required")

    products = db.query(CategoryProduct).filter(
        CategoryProduct.id.in_(req.product_ids)
    ).all()

    if not products:
        raise HTTPException(404, "No products found")

    for product in products:
        background_tasks.add_task(_fetch_single_detail, product.id)

    return {
        'message': f'Fetching details for {len(products)} products in background',
        'product_ids': [p.id for p in products],
    }


@router.post("/bulk-fetch")
async def bulk_fetch_details(req: BulkFetchRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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

    for product in products:
        background_tasks.add_task(_fetch_single_detail, product.id)

    return {
        'message': f'Bulk fetching details for {len(products)} products in background',
        'count': len(products),
    }


@router.get("/products/{product_id}")
async def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    product = db.query(CategoryProduct).filter(CategoryProduct.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    return _serialize_product(product)


@router.get("/session-url-lookup")
async def session_url_lookup(
    category: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    if not category:
        return {'category_url': None}

    q = db.query(CategorySession).filter(CategorySession.category_name.ilike(f"%{category}%"))
    if platform:
        q = q.filter(CategorySession.platform == platform)
    session = q.order_by(CategorySession.created_at.desc()).first()
    if session:
        return {'category_url': session.category_url, 'session_id': str(session.id), 'category_name': session.category_name}
    return {'category_url': None}


@router.get("/products-by-category")
async def list_products_by_category(
    category: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    q = db.query(CategoryProduct).join(CategorySession, CategoryProduct.session_id == CategorySession.id)

    if platform:
        q = q.filter(CategorySession.platform == platform)
    if category:
        q = q.filter(CategorySession.category_name.ilike(f"%{category}%"))
    if search:
        q = q.filter(or_(
            CategoryProduct.name.ilike(f"%{search}%"),
            CategoryProduct.brand.ilike(f"%{search}%"),
        ))

    total = q.count()

    stats_row = q.with_entities(
        func.avg(CategoryProduct.price),
        func.count(func.distinct(CategoryProduct.brand)),
    ).first()

    q = q.order_by(CategoryProduct.position.asc())
    offset = (page - 1) * page_size
    products = q.offset(offset).limit(page_size).all()

    sessions_q = db.query(CategorySession)
    if platform:
        sessions_q = sessions_q.filter(CategorySession.platform == platform)
    if category:
        sessions_q = sessions_q.filter(CategorySession.category_name.ilike(f"%{category}%"))
    related_sessions = sessions_q.order_by(CategorySession.created_at.desc()).limit(5).all()

    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size if total > 0 else 0,
        'products': [_serialize_product(p) for p in products],
        'filtered_stats': {
            'avg_price': float(stats_row[0]) if stats_row[0] else 0,
            'brand_count': stats_row[1] or 0,
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
    }
