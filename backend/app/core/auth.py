"""
Supabase JWT tabanlı kullanıcı doğrulama middleware'i.

Supabase Auth'dan gelen JWT token'ı doğrular ve kullanıcıyı
veritabanında bulur veya ilk girişte otomatik oluşturur.
"""

import logging
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Supabase JWT'den kullanıcıyı doğrula ve döndür."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header gerekli")

    token = auth_header[7:]  # "Bearer " prefix'ini kaldır

    try:
        jwt_secret = settings.SUPABASE_JWT_SECRET
        if jwt_secret:
            payload = jwt.decode(
                token, jwt_secret, algorithms=["HS256"], audience="authenticated"
            )
        else:
            # JWT secret yoksa doğrulama olmadan decode et (sadece geliştirme)
            payload = jwt.decode(
                token, options={"verify_signature": False}, algorithms=["HS256"]
            )
            logger.warning(
                "SUPABASE_JWT_SECRET ayarlanmadı — JWT imza doğrulaması atlanıyor!"
            )
    except JWTError as e:
        logger.warning(f"JWT doğrulama hatası: {e}")
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token'da kullanıcı ID bulunamadı")

    user_email = payload.get("email", "")

    # Kullanıcıyı veritabanında bul veya oluştur (ilk giriş)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=user_email,
            full_name=payload.get("user_metadata", {}).get("full_name", ""),
            plan_tier="free",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Yeni kullanıcı oluşturuldu: {user_email} ({user_id})")

    return user


async def get_optional_user(
    request: Request, db: Session = Depends(get_db)
):
    """Opsiyonel auth — token varsa kullanıcıyı döndür, yoksa None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
