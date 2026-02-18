import hmac
from fastapi import HTTPException, Request

from app.core.config import settings

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def require_mutating_api_key(request: Request) -> None:
    """Require X-API-Key on mutating API routes."""
    if request.method not in MUTATING_METHODS:
        return

    expected_api_key = settings.require_internal_api_key()
    provided_api_key = request.headers.get("x-api-key")

    if not provided_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required")

    if not hmac.compare_digest(provided_api_key, expected_api_key):
        raise HTTPException(status_code=403, detail="Invalid X-API-Key")
