import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)

_db_initialized = False


def _init_db():
    global _db_initialized
    try:
        from app.db.database import get_engine
        from sqlalchemy import text
        eng = get_engine()
        # Verify DB connectivity (schema managed by Alembic)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        _db_initialized = True
        logger.info("Database connection verified successfully")
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.config import settings
    api_key = (settings.INTERNAL_API_KEY or "").strip()
    if not api_key:
        logger.warning(
            "INTERNAL_API_KEY is not set. Mutating API endpoints will reject requests."
        )

    try:
        from app.core.logger import setup_uvicorn_log_filter
        setup_uvicorn_log_filter()
    except Exception:
        pass

    _init_db()

    yield


def _get_cors_origins():
    try:
        from app.core.config import settings
        origins = settings.cors_allowed_origins()
        if not origins:
            logger.warning("CORS: Empty origin list — cross-origin requests will be blocked")
        return origins
    except Exception as e:
        logger.error(f"CORS configuration failed: {e}")
        # Last defense: read REPLIT_DOMAINS directly
        replit_domains = os.getenv("REPLIT_DOMAINS", "")
        if replit_domains:
            fallback = []
            for domain in replit_domains.split(","):
                d = domain.strip()
                if d:
                    fallback.append(f"https://{d}")
            if fallback:
                logger.warning(f"CORS: Using REPLIT_DOMAINS fallback: {fallback}")
                return fallback
        return []


app = FastAPI(
    title="Pazaryeri Veri Analiz API",
    description="Marketplace Data Analysis Platform API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "db_initialized": _db_initialized}


@app.get("/health/deep")
async def health_deep():
    from app.core.config import settings

    db_reachable = False
    try:
        from sqlalchemy import text
        from app.db.database import get_engine
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db_reachable = True
    except Exception:
        pass

    q_reachable = False
    client = None
    try:
        from redis import Redis
        client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        q_reachable = bool(client.ping())
    except Exception:
        pass
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass

    return {
        "status": "healthy",
        "db_initialized": _db_initialized,
        "scraper_api_configured": settings.has_scraper_api(),
        "price_monitor_executor": settings.price_monitor_executor(),
        "database_reachable": db_reachable,
        "queue_reachable": q_reachable,
    }


from app.api.routes import router
from app.api.url_scraper_routes import router as url_scraper_router
from app.api.transcript_routes import router as transcript_router
from app.api.json_editor_routes import router as json_editor_router
from app.api.store_product_routes import router as store_product_router
from app.api.category_explorer_routes import router as category_explorer_router

app.include_router(router, prefix="/api")
app.include_router(url_scraper_router)
app.include_router(transcript_router)
app.include_router(json_editor_router)
app.include_router(store_product_router)
app.include_router(category_explorer_router)

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        frontend_root = Path(frontend_dist).resolve()
        requested = (frontend_root / full_path).resolve()
        if full_path and requested.is_file() and frontend_root in requested.parents:
            return FileResponse(str(requested))
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
else:
    @app.get("/")
    async def root():
        return {"message": "Pazaryeri Veri Analiz API", "status": "running"}
