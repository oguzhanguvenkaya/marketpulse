# MarketPulse - Pazaryeri Veri Analiz Platformu

Marketplace Data Analysis Platform for Turkish e-commerce marketplaces. Scrapes product data from Hepsiburada and Trendyol, tracks seller prices, monitors sponsored ads, and delivers AI-powered insights.

## Features

| Feature | Description |
|---------|-------------|
| **Keyword Search** | Search products on Hepsiburada, collect up to 8 products per query with full detail extraction |
| **Product Intelligence** | Two-stage scraping: listing page → detail page. Extracts price, brand, SKU, barcode, ratings, reviews, stock, coupons, campaigns |
| **Sponsored Ads Tracking** | Detects sponsored products and brand carousel ads from search results |
| **Price Monitor** | Track seller prices for specific SKUs across Hepsiburada and Trendyol. Bulk import, threshold alerts, buybox tracking |
| **Seller Analysis** | Analyze sellers by products, pricing, stock, and merchant ratings |
| **URL Scraper** | Scrape any product URL (single, bulk JSON, or CSV upload). Extracts meta tags, JSON-LD, Open Graph data |
| **Video Transcripts** | Extract YouTube video transcripts (single, bulk, or CSV). Auto-detects language |
| **JSON Editor** | Edit product catalog JSON files with dynamic field rendering and PostgreSQL persistence |
| **AI Analysis** | GPT-4o-mini powered insights from collected product data |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Celery |
| Frontend | React 19, TypeScript, Vite 7, TailwindCSS v4, Plotly.js |
| Database | PostgreSQL (Neon) |
| Queue | Redis + Celery |
| Proxy | ScraperAPI (primary), Bright Data (fallback) |
| Scraping | Playwright + playwright-stealth, BeautifulSoup4, aiohttp |
| AI | OpenAI GPT-4o-mini |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   │   ├── routes.py      # Main routes (search, products, price-monitor, sellers, ads)
│   │   │   ├── url_scraper_routes.py
│   │   │   ├── transcript_routes.py
│   │   │   └── json_editor_routes.py
│   │   ├── core/              # Configuration, security, logging
│   │   │   ├── config.py      # Settings (env vars, proxy config)
│   │   │   ├── security.py    # API key middleware
│   │   │   └── logger.py      # Logging setup
│   │   ├── db/                # Database layer
│   │   │   ├── database.py    # SQLAlchemy engine & session
│   │   │   └── models.py      # All ORM models (13 tables)
│   │   ├── services/          # Business logic
│   │   │   ├── scraping.py    # Hepsiburada scraping with Playwright
│   │   │   ├── price_monitor_service.py      # Hepsiburada price monitoring
│   │   │   ├── trendyol_price_monitor_service.py  # Trendyol price monitoring
│   │   │   ├── proxy_providers.py  # Modular proxy system (ScraperAPI/BrightData/Direct)
│   │   │   ├── llm_service.py      # OpenAI integration
│   │   │   ├── url_scraper_service.py    # Generic URL scraping
│   │   │   └── transcript_service.py     # YouTube transcript extraction
│   │   ├── tasks.py           # Celery task definitions
│   │   └── main.py            # FastAPI app initialization
│   ├── scripts/               # Utility scripts
│   │   ├── runtime_preflight.py
│   │   ├── e2e_fetch_smoke.py
│   │   └── reactivate_auth_failed_inactive.py
│   ├── requirements.txt
│   └── run.py                 # Uvicorn entry point
├── frontend/
│   ├── src/
│   │   ├── pages/             # 10 page components (lazy-loaded)
│   │   ├── components/        # Shared components (Layout)
│   │   ├── services/          # API client & query cache
│   │   ├── App.tsx            # Router setup
│   │   └── main.tsx           # Entry point
│   └── dist/                  # Production build output
├── ARCHITECTURE.md            # System architecture reference
├── replit.md                  # AI agent context file
└── README.md                  # This file
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `INTERNAL_API_KEY` | API key for mutating endpoints (X-API-Key header) |
| `SCRAPER_API_KEY` | ScraperAPI key (fallback names: `SCRAPPER_API`, `SCRAPPPER_API`) |
| `OPENAI_API_KEY` | OpenAI API key for AI analysis |
| `REDIS_URL` | Redis connection URL (default: `redis://localhost:6379/0`) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `PRICE_MONITOR_EXECUTOR` | `celery` | Execution mode: `celery` or `local` |
| `PRICE_MONITOR_MAX_CONCURRENT_REQUESTS` | `17` | Max concurrent price fetch requests |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `PROXY_PROVIDER` | `auto` | Proxy mode: `auto`, `scraperapi`, `brightdata`, `direct` |
| `DB_POOL_SIZE` | `5` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | `10` | SQLAlchemy max overflow |
| `DB_POOL_TIMEOUT_SECONDS` | `30` | Pool checkout timeout |
| `DB_POOL_RECYCLE_SECONDS` | `180` | Connection recycle interval |
| `DEBUG_SAVE_HTML` | `true` | Save HTML on scraping errors |
| `BRIGHT_DATA_ACCOUNT_ID` | - | Bright Data customer ID |
| `BRIGHT_DATA_ZONE_NAME` | - | Bright Data zone |
| `BRIGHT_DATA_ZONE_PASSWORD` | - | Bright Data zone password |
| `VITE_QUERY_CACHE_TTL_MS` | `45000` | Frontend query cache TTL |
| `VITE_INTERNAL_API_KEY` | - | API key injected into frontend |

## Running Locally

### 1. Redis
```bash
redis-server
```

### 2. Backend API
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Celery Worker
```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

### 4. Frontend
```bash
cd frontend
npm run dev
```

## Running on Replit

Backend and frontend workflows are pre-configured. The backend serves on port 8000 and the frontend dev server on port 5000 (configured in `vite.config.ts`). Set required secrets in the Secrets tab.

## Health Check

```
GET /health
```

Returns:
```json
{
  "status": "healthy",
  "scraper_api_configured": true,
  "price_monitor_executor": "celery",
  "database_reachable": true,
  "queue_reachable": true
}
```

## Verification Scripts

```bash
cd backend
python3 scripts/runtime_preflight.py --timeout 2
python3 scripts/e2e_fetch_smoke.py --base-url http://127.0.0.1:8000 --platform hepsiburada --fetch-type active
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Fetch starts but doesn't progress | Confirm Redis and Celery worker are running. Check `/health` |
| `POST /api/price-monitor/fetch` returns 503 | Redis unreachable. Verify `REDIS_URL` and Redis process |
| Frequent DB connection drops | Keep `DB_POOL_RECYCLE_SECONDS` low (180). Verify Neon SSL params |
| UI repeatedly re-fetches endpoints | Check `VITE_QUERY_CACHE_TTL_MS`. Run `request_frequency_qa.py` |
| ScraperAPI failures | Check API key. Verify with `/health` endpoint. Check debug HTML in `/tmp/scraping_debug/` |
