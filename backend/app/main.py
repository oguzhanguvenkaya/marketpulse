import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from redis import Redis
from sqlalchemy import text
from app.api.routes import router
from app.api.url_scraper_routes import router as url_scraper_router
from app.api.transcript_routes import router as transcript_router
from app.api.json_editor_routes import router as json_editor_router
from app.api.store_product_routes import router as store_product_router
from app.core.config import settings
from app.db.database import engine, Base
from app.core.logger import setup_uvicorn_log_filter

Base.metadata.create_all(bind=engine)

setup_uvicorn_log_filter()

settings.require_internal_api_key()
cors_allowed_origins = settings.cors_allowed_origins()

app = FastAPI(
    title="Pazaryeri Veri Analiz API",
    description="Marketplace Data Analysis Platform API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


def _database_reachable() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _queue_reachable() -> bool:
    client = None
    try:
        client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        return bool(client.ping())
    except Exception:
        return False
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "scraper_api_configured": settings.has_scraper_api(),
        "price_monitor_executor": settings.price_monitor_executor(),
        "database_reachable": _database_reachable(),
        "queue_reachable": _queue_reachable(),
    }

app.include_router(router, prefix="/api")
app.include_router(url_scraper_router)
app.include_router(transcript_router)
app.include_router(json_editor_router)
app.include_router(store_product_router)

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
else:
    @app.get("/")
    async def root():
        return {"message": "Pazaryeri Veri Analiz API", "status": "running"}
