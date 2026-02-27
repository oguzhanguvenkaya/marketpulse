"""Rakip Satıcı Takibi API endpoint'leri."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional

from app.db.database import get_db
from app.db.models import User, MonitoredProduct, CompetitorSeller, CompetitorProduct
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/competitors", tags=["Competitors"])


class AddCompetitorRequest(BaseModel):
    platform: str
    seller_id: str
    seller_name: str
    seller_url: Optional[str] = None
    seller_rating: Optional[float] = None
    notes: Optional[str] = None


class AddProductRequest(BaseModel):
    sku: Optional[str] = None
    product_name: Optional[str] = None
    product_url: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    is_sponsored: bool = False


class UpdateCompetitorRequest(BaseModel):
    seller_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("")
async def add_competitor(
    request: AddCompetitorRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rakip satıcı ekle."""
    # Duplicate kontrolü
    existing = db.query(CompetitorSeller).filter(
        CompetitorSeller.user_id == user.id,
        CompetitorSeller.platform == request.platform,
        CompetitorSeller.seller_id == request.seller_id,
    ).first()

    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.commit()
            return {"id": str(existing.id), "message": "Rakip yeniden aktifleştirildi"}
        raise HTTPException(400, "Bu rakip zaten takip ediliyor")

    competitor = CompetitorSeller(
        user_id=user.id,
        platform=request.platform,
        seller_id=request.seller_id,
        seller_name=request.seller_name,
        seller_url=request.seller_url,
        seller_rating=request.seller_rating,
        notes=request.notes,
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)

    return {"id": str(competitor.id), "message": "Rakip eklendi"}


@router.get("")
async def list_competitors(
    platform: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının rakip satıcılarını listele."""
    query = db.query(CompetitorSeller).filter(
        CompetitorSeller.user_id == user.id,
        CompetitorSeller.is_active == True,
    )
    if platform:
        query = query.filter(CompetitorSeller.platform == platform)

    competitors = query.order_by(desc(CompetitorSeller.created_at)).all()

    result = []
    for c in competitors:
        product_count = db.query(func.count(CompetitorProduct.id)).filter(
            CompetitorProduct.competitor_id == c.id,
        ).scalar() or 0

        result.append({
            "id": str(c.id),
            "platform": c.platform,
            "seller_id": c.seller_id,
            "seller_name": c.seller_name,
            "seller_url": c.seller_url,
            "seller_rating": c.seller_rating,
            "seller_rating_count": c.seller_rating_count,
            "total_products": product_count,
            "notes": c.notes,
            "last_checked_at": c.last_checked_at.isoformat() if c.last_checked_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"competitors": result, "total": len(result)}


@router.get("/{competitor_id}")
async def get_competitor_detail(
    competitor_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rakip detay + ürünleri."""
    competitor = db.query(CompetitorSeller).filter(
        CompetitorSeller.id == competitor_id,
        CompetitorSeller.user_id == user.id,
    ).first()

    if not competitor:
        raise HTTPException(404, "Rakip bulunamadı")

    products = db.query(CompetitorProduct).filter(
        CompetitorProduct.competitor_id == competitor.id,
    ).order_by(desc(CompetitorProduct.last_seen_at)).limit(100).all()

    return {
        "competitor": {
            "id": str(competitor.id),
            "platform": competitor.platform,
            "seller_id": competitor.seller_id,
            "seller_name": competitor.seller_name,
            "seller_url": competitor.seller_url,
            "seller_rating": competitor.seller_rating,
            "notes": competitor.notes,
            "total_products": len(products),
        },
        "products": [
            {
                "id": str(p.id),
                "sku": p.sku,
                "product_name": p.product_name,
                "product_url": p.product_url,
                "price": float(p.price) if p.price else None,
                "original_price": float(p.original_price) if p.original_price else None,
                "category": p.category,
                "image_url": p.image_url,
                "is_sponsored": p.is_sponsored,
                "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
            }
            for p in products
        ],
    }


@router.put("/{competitor_id}")
async def update_competitor(
    competitor_id: str,
    request: UpdateCompetitorRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rakip bilgilerini güncelle."""
    competitor = db.query(CompetitorSeller).filter(
        CompetitorSeller.id == competitor_id,
        CompetitorSeller.user_id == user.id,
    ).first()

    if not competitor:
        raise HTTPException(404, "Rakip bulunamadı")

    if request.seller_name is not None:
        competitor.seller_name = request.seller_name
    if request.notes is not None:
        competitor.notes = request.notes
    if request.is_active is not None:
        competitor.is_active = request.is_active

    db.commit()
    return {"status": "ok"}


@router.delete("/{competitor_id}")
async def remove_competitor(
    competitor_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rakibi kaldır (soft delete)."""
    competitor = db.query(CompetitorSeller).filter(
        CompetitorSeller.id == competitor_id,
        CompetitorSeller.user_id == user.id,
    ).first()

    if not competitor:
        raise HTTPException(404, "Rakip bulunamadı")

    competitor.is_active = False
    db.commit()
    return {"status": "ok"}


@router.post("/{competitor_id}/products")
async def add_competitor_product(
    competitor_id: str,
    request: AddProductRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rakibe ürün ekle."""
    competitor = db.query(CompetitorSeller).filter(
        CompetitorSeller.id == competitor_id,
        CompetitorSeller.user_id == user.id,
    ).first()

    if not competitor:
        raise HTTPException(404, "Rakip bulunamadı")

    product = CompetitorProduct(
        competitor_id=competitor.id,
        sku=request.sku,
        product_name=request.product_name,
        product_url=request.product_url,
        price=request.price,
        original_price=request.original_price,
        category=request.category,
        image_url=request.image_url,
        is_sponsored=request.is_sponsored,
    )
    db.add(product)

    # Toplam ürün sayısını güncelle
    competitor.total_products = db.query(func.count(CompetitorProduct.id)).filter(
        CompetitorProduct.competitor_id == competitor.id,
    ).scalar() + 1

    db.commit()
    return {"id": str(product.id), "message": "Ürün eklendi"}


@router.get("/{competitor_id}/overlap")
async def get_competitor_overlap(
    competitor_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rakip ile kullanıcının ortak SKU'larını bul."""
    competitor = db.query(CompetitorSeller).filter(
        CompetitorSeller.id == competitor_id,
        CompetitorSeller.user_id == user.id,
    ).first()

    if not competitor:
        raise HTTPException(404, "Rakip bulunamadı")

    # Rakibin SKU'ları
    comp_skus = db.query(CompetitorProduct.sku).filter(
        CompetitorProduct.competitor_id == competitor.id,
        CompetitorProduct.sku.isnot(None),
    ).all()
    comp_sku_set = {s[0] for s in comp_skus if s[0]}

    # Kullanıcının SKU'ları
    user_products = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user.id,
        MonitoredProduct.platform == competitor.platform,
        MonitoredProduct.is_active == True,
    ).all()

    overlapping = []
    for product in user_products:
        if product.sku in comp_sku_set:
            overlapping.append({
                "sku": product.sku,
                "product_name": product.product_name,
                "product_id": str(product.id),
            })

    return {
        "competitor_name": competitor.seller_name,
        "total_competitor_products": len(comp_sku_set),
        "total_user_products": len(user_products),
        "overlapping_count": len(overlapping),
        "overlapping_products": overlapping,
    }


@router.get("/comparison/all")
async def compare_all_competitors(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tüm rakipleri karşılaştır."""
    competitors = db.query(CompetitorSeller).filter(
        CompetitorSeller.user_id == user.id,
        CompetitorSeller.is_active == True,
    ).all()

    comparison = []
    for c in competitors:
        stats = db.query(
            func.count(CompetitorProduct.id).label("count"),
            func.avg(CompetitorProduct.price).label("avg_price"),
            func.min(CompetitorProduct.price).label("min_price"),
            func.max(CompetitorProduct.price).label("max_price"),
        ).filter(
            CompetitorProduct.competitor_id == c.id,
        ).first()

        comparison.append({
            "id": str(c.id),
            "seller_name": c.seller_name,
            "platform": c.platform,
            "seller_rating": c.seller_rating,
            "product_count": stats.count if stats else 0,
            "avg_price": round(float(stats.avg_price), 2) if stats and stats.avg_price else None,
            "min_price": float(stats.min_price) if stats and stats.min_price else None,
            "max_price": float(stats.max_price) if stats and stats.max_price else None,
        })

    return {"competitors": comparison}
