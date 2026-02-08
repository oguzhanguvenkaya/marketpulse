import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router
from app.api.url_scraper_routes import router as url_scraper_router
from app.api.transcript_routes import router as transcript_router
from app.api.json_editor_routes import router as json_editor_router
from app.db.database import engine, Base
from app.core.logger import setup_uvicorn_log_filter

Base.metadata.create_all(bind=engine)

setup_uvicorn_log_filter()

app = FastAPI(
    title="Pazaryeri Veri Analiz API",
    description="Marketplace Data Analysis Platform API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(url_scraper_router)
app.include_router(transcript_router)
app.include_router(json_editor_router)

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "Pazaryeri Veri Analiz API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
