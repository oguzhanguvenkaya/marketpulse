# Backend - FastAPI

## Directory Structure

```
backend/
├── app/
│   ├── api/                        # Route handlers
│   │   ├── routes.py               # Main API (2100+ lines)
│   │   │   ├── /api/search         # Keyword search
│   │   │   ├── /api/products       # Product CRUD & snapshots
│   │   │   ├── /api/price-monitor  # Price monitoring
│   │   │   ├── /api/sellers        # Seller analysis
│   │   │   ├── /api/analyze        # AI analysis
│   │   │   └── /api/stats          # Dashboard stats
│   │   ├── url_scraper_routes.py   # /api/url-scraper/*
│   │   ├── transcript_routes.py    # /api/transcripts/*
│   │   └── json_editor_routes.py   # /api/json-editor/*
│   │
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   │   ├── Database config (pool size, overflow, recycle)
│   │   │   ├── Proxy config (ScraperAPI, Bright Data)
│   │   │   └── Validation methods (require_*)
│   │   ├── security.py             # API key middleware (X-API-Key header)
│   │   └── logger.py               # Structured logging, uvicorn filter
│   │
│   ├── db/
│   │   ├── database.py             # SQLAlchemy engine, SessionLocal, get_db
│   │   └── models.py              # 13 ORM models
│   │       ├── Product, ProductSnapshot, ProductSeller, ProductReview
│   │       ├── SearchTask, SponsoredBrandAd, SearchSponsoredProduct
│   │       ├── MonitoredProduct, SellerSnapshot, PriceMonitorTask
│   │       ├── ScrapeJob, ScrapeResult
│   │       ├── TranscriptJob, TranscriptResult
│   │       └── JsonFile
│   │
│   ├── services/
│   │   ├── scraping.py             # ScrapingService
│   │   │   ├── Browser management (Playwright + stealth)
│   │   │   ├── Hepsiburada search scraping
│   │   │   ├── Product detail extraction (utagData, JSON-LD, HTML)
│   │   │   └── Sponsored ad detection
│   │   ├── price_monitor_service.py      # Hepsiburada price monitor
│   │   │   ├── Merchant API calls (listing page API)
│   │   │   ├── Seller snapshot creation
│   │   │   └── Campaign price extraction
│   │   ├── trendyol_price_monitor_service.py  # Trendyol price monitor
│   │   ├── proxy_providers.py      # Proxy abstraction layer
│   │   │   ├── ScraperAPIProvider (primary, cheaper)
│   │   │   ├── BrightDataProvider (fallback, premium)
│   │   │   ├── DirectProvider (no proxy, last resort)
│   │   │   ├── ProxyManager (auto-selection, fallback chain)
│   │   │   └── DebugLogger (request logging, HTML saving)
│   │   ├── llm_service.py          # OpenAI GPT-4o-mini integration
│   │   ├── url_scraper_service.py  # Generic URL scraping (15 workers)
│   │   └── transcript_service.py   # YouTube transcript extraction (10 workers)
│   │
│   ├── tasks.py                    # Celery app + task definitions
│   │   ├── celery_app config (Redis broker/backend)
│   │   ├── run_scraping_task
│   │   └── run_price_monitor_fetch_task
│   │
│   └── main.py                     # FastAPI app init
│       ├── CORS middleware
│       ├── Health endpoint (/health)
│       ├── Router mounting
│       └── SPA static file serving (frontend/dist)
│
├── scripts/
│   ├── runtime_preflight.py        # DB + queue connectivity check
│   ├── e2e_fetch_smoke.py          # End-to-end fetch test
│   └── reactivate_auth_failed_inactive.py
│
├── requirements.txt
└── run.py                          # uvicorn startup (port 8000, reload mode)
```

## Running

```bash
cd backend
python run.py                    # Starts uvicorn on 0.0.0.0:8000
```

Or directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Celery Worker

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

## Security

All mutating API endpoints require `X-API-Key` header matching `INTERNAL_API_KEY` env var. This is enforced by `require_mutating_api_key` dependency in `security.py`.

## Database

SQLAlchemy with PostgreSQL. Tables are auto-created on startup via `Base.metadata.create_all()`.

Connection pool settings are tuned for Neon (serverless Postgres):
- `DB_POOL_RECYCLE_SECONDS=180` prevents stale connections
- Retry logic for transient `OperationalError`s

## Proxy System

Configured via `PROXY_PROVIDER` env var. The `ProxyManager` in `proxy_providers.py` handles automatic provider selection and fallback.

Debug HTML is saved to `/tmp/scraping_debug/` when `DEBUG_SAVE_HTML=true`.
