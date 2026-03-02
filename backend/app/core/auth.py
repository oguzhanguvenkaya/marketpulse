"""
Supabase JWT tabanlı kullanıcı doğrulama middleware'i.

Supabase Auth'dan gelen JWT token'ı doğrular ve kullanıcıyı
veritabanında bulur veya ilk girişte otomatik oluşturur.

ES256 (JWK) ve HS256 destekler.
"""

import json
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

# JWK anahtarını bir kez parse et ve cache'le
_jwk_key: Optional[dict] = None


def _get_jwk_key() -> Optional[dict]:
    """SUPABASE_JWT_JWK env'den JWK dict döndür (cache'li)."""
    global _jwk_key
    if _jwk_key is not None:
        return _jwk_key

    raw = settings.SUPABASE_JWT_JWK
    if not raw:
        return None

    try:
        _jwk_key = json.loads(raw)
        logger.info("Supabase JWT JWK (ES256) yüklendi — kid: %s", _jwk_key.get("kid", "?"))
        return _jwk_key
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("SUPABASE_JWT_JWK parse hatası: %s", e)
        return None


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Supabase JWT'den kullanıcıyı doğrula ve döndür."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header gerekli")

    token = auth_header[7:]  # "Bearer " prefix'ini kaldır

    try:
        jwk_key = _get_jwk_key()
        jwt_secret = settings.SUPABASE_JWT_SECRET

        if jwk_key:
            # ES256 — JWK public key ile doğrula
            payload = jwt.decode(
                token, jwk_key, algorithms=["ES256"], audience="authenticated"
            )
        elif jwt_secret:
            # HS256 — symmetric secret ile doğrula
            payload = jwt.decode(
                token, jwt_secret, algorithms=["HS256"], audience="authenticated"
            )
        else:
            # Dev mode — doğrulama olmadan decode
            payload = jwt.decode(
                token, "", options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_exp": False,
                }, algorithms=["HS256"]
            )
            logger.warning(
                "SUPABASE_JWT_SECRET/JWK ayarlanmadı — JWT imza doğrulaması atlanıyor!"
            )
    except JWTError as e:
        logger.warning("JWT doğrulama hatası: %s", e)
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
        logger.info("Yeni kullanıcı oluşturuldu: %s (%s)", user_email, user_id)

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
