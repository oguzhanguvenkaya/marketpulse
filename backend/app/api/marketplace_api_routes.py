"""Marketplace API Entegrasyon routes — magaza baglama, urun ve siparis cekme."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.marketplace_api_service import marketplace_api_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketplace-api", tags=["Marketplace API"])


class ConnectStoreRequest(BaseModel):
    platform: str
    credentials: dict  # {api_key, api_secret, seller_id, ...}


class ConnectStoreResponse(BaseModel):
    success: bool
    platform: Optional[str] = None
    store_name: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.get("/platforms")
async def get_supported_platforms(user: User = Depends(get_current_user)):
    """Desteklenen marketplace platformlarini dondur."""
    return marketplace_api_service.get_supported_platforms()


@router.post("/connect", response_model=ConnectStoreResponse)
async def connect_store(
    req: ConnectStoreRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanicinin magazasini bagla ve test et."""
    result = await marketplace_api_service.connect_store(user, req.platform, req.credentials, db)
    if result.get("error"):
        return ConnectStoreResponse(
            success=False,
            platform=req.platform,
            error=result["error"],
        )
    return ConnectStoreResponse(
        success=True,
        platform=result["platform"],
        store_name=result.get("store_name"),
        message=result.get("message"),
    )


@router.post("/test-connection")
async def test_connection(
    req: ConnectStoreRequest,
    user: User = Depends(get_current_user),
):
    """Marketplace API baglanti testi (kaydetmeden)."""
    result = await marketplace_api_service._test_connection(req.platform, req.credentials)
    return result


@router.get("/store/products")
async def get_store_products(
    platform: str,
    page: int = 0,
    size: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bagli magazanin urunlerini listele."""
    # TODO: DB'den credentials cek
    return await marketplace_api_service.get_store_products(platform, {}, page, size)


@router.get("/store/orders")
async def get_store_orders(
    platform: str,
    days: int = 7,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bagli magazanin siparislerini listele."""
    return await marketplace_api_service.get_store_orders(platform, {}, days)
