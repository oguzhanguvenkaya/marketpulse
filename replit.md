# Pazaryeri Veri Analiz Platformu (MarketPulse)

## Overview
The Marketplace Data Analysis Platform empowers marketplace sellers and marketing agencies with data-driven decision-making capabilities. It scrapes product data from major Turkish marketplaces (Hepsiburada, Trendyol), analyzes market trends, tracks seller prices, monitors sponsored ads, and delivers AI-powered insights. The platform serves as a tool for competitive analysis, strategic pricing, and understanding market dynamics within the e-commerce landscape.

## User Preferences
- English language UI with Palantir-style dark theme
- Focus on Hepsiburada marketplace initially, Trendyol support added for price monitoring
- Limit to 8 products per search to manage costs
- ScraperAPI as primary (cheaper), Bright Data for fallback

## UI Theme
- Dark color palette: dark-900 (#0a0b0d) to dark-300 (#3d434e)
- Accent color: Cyan (#00d4ff) for primary actions and highlights
- Status colors: Success green, Warning orange, Danger red with glow variants
- Reusable components: card-dark, btn-primary/secondary, input-dark, table-dark, badges, stat-card
- Subtle animations: fade-in, slide-in, pulse-glow effects

## System Architecture
The platform is built with a clear separation of concerns, featuring a FastAPI backend (port 8000) and a React frontend (port 5173 dev / static served by backend in production). It employs a robust, two-stage scraping strategy for comprehensive data collection and a modular proxy architecture for reliable data acquisition. Celery + Redis handle async task execution for price monitoring and search jobs.

### Backend Structure
```
backend/app/
├── api/           → Route handlers (routes.py, url_scraper_routes.py, transcript_routes.py, json_editor_routes.py)
├── core/          → config.py (Settings), security.py (API key auth), logger.py
├── db/            → database.py (SQLAlchemy engine), models.py (13 ORM models)
├── services/      → scraping.py, price_monitor_service.py, trendyol_price_monitor_service.py,
│                    proxy_providers.py, llm_service.py, url_scraper_service.py, transcript_service.py
├── tasks.py       → Celery app + task definitions (run_scraping_task, run_price_monitor_fetch_task)
└── main.py        → FastAPI app init, CORS, health endpoint, SPA serving
```

### Frontend Structure
```
frontend/src/
├── pages/         → 10 lazy-loaded pages (Dashboard, Products, ProductDetail, Ads, PriceMonitor,
│                    Sellers, SellerDetail, UrlScraper, VideoTranscripts, JsonEditor)
├── components/    → Layout.tsx (sidebar, header, mobile menu)
├── services/      → api.ts (Axios client, 700+ lines), queryCache.ts (TTL-based cache)
├── App.tsx        → Router setup
└── main.tsx       → Entry point
```

## Features

### Two-Stage Scraping
Products are first identified from search/listing pages, then individual product detail pages are visited to extract extensive data. This includes parsing `utagData` JavaScript objects, JSON-LD schema, and various HTML elements to gather product name, brand, category, price, SKU, barcode, seller information, ratings, reviews, stock status, discounted prices, coupons, and campaign details.

### Price Monitoring System
Allows distributors to track seller prices across Hepsiburada and Trendyol for specific SKUs. Supports bulk product imports and initiates Celery tasks for fetching price data. Captures merchant name, price, original price, campaign price, stock, buybox order, shipping info, and campaign tags. Features threshold alerts, inactive SKU tracking, stop/resume, and CSV export.

### Sponsored Ads Tracking
Identifies individual sponsored products and groups them to track brand advertisers. Parses advertisement-specific HTML classes and decodes tracking URLs to extract real product information and associated seller data.

### AI Analysis
Integrates OpenAI's GPT-4o-mini for generating insights from collected product data.

### Modular Proxy System
Features an "auto" mode that prioritizes ScraperAPI (cheaper) and falls back to Bright Data (premium, for bot protection bypass). Includes debug logging and HTML saving to `/tmp/scraping_debug/` for troubleshooting.

### URL Scraper
Generic URL scraping system. Supports single URL, bulk JSON, and CSV upload. Uses ScraperAPI to fetch pages, extracts data via meta tags, JSON-LD, Open Graph, and HTML parsing. 15 concurrent workers with stop/resume. DB models: `ScrapeJob`, `ScrapeResult`. Routes: `/api/url-scraper/`.

### YouTube Video Transcript Scraper
Extracts transcripts using `youtube-transcript-api`. Supports single URL, bulk JSON, and CSV upload (auto-detects Video_URL columns). 10 concurrent workers with stop/resume. DB models: `TranscriptJob`, `TranscriptResult`. Routes: `/api/transcripts/`. Frontend: `/video-transcripts`.

### JSON Product Editor
Full-stack tool for editing product catalog JSON files with PostgreSQL persistence. Fully dynamic rendering: all product keys auto-detected and rendered based on value type. Supports any JSON structure. DB model: `JsonFile`. Routes: `/api/json-editor/`. Frontend: `/json-editor`.

## Database Models (13 tables)
- `Product`, `ProductSnapshot`, `ProductSeller`, `ProductReview`
- `SearchTask`, `SponsoredBrandAd`, `SearchSponsoredProduct`
- `MonitoredProduct`, `SellerSnapshot`, `PriceMonitorTask`
- `ScrapeJob`, `ScrapeResult`
- `TranscriptJob`, `TranscriptResult`
- `JsonFile`

## Key API Route Groups
- `/api/search`, `/api/products`, `/api/stats` → Main search and product routes
- `/api/price-monitor/*` → Price monitoring (products, fetch, sellers, export)
- `/api/sellers/*` → Seller analysis and export
- `/api/url-scraper/*` → URL scraping jobs
- `/api/transcripts/*` → YouTube transcript jobs
- `/api/json-editor/*` → JSON file management
- `/health` → System health check

## Celery Tasks
- `run_scraping_task`: Execute keyword search via Playwright and save products
- `run_price_monitor_fetch_task`: Fetch prices for monitored products (Hepsiburada or Trendyol)
- Broker/Backend: Redis (`REDIS_URL`)

## External Dependencies
- **Database:** PostgreSQL (Neon-backed on Replit)
- **Queue:** Redis (Celery broker/backend)
- **AI Service:** OpenAI (GPT-4o-mini)
- **Proxy Services:**
    - ScraperAPI (Primary, cost-effective)
    - Bright Data Residential Proxy (Fallback, premium)
- **Frontend Libraries:**
    - React 19, TypeScript, Vite 7, TailwindCSS v4, Plotly.js, React Router DOM v7, Axios
- **Backend Libraries:**
    - Python 3.11, FastAPI 0.109, SQLAlchemy 2.0, Celery 5.3, Redis 5.0
    - Playwright 1.41 + playwright-stealth 2.0, BeautifulSoup4 4.12, aiohttp 3.13
    - OpenAI 1.12, youtube-transcript-api 1.2

## Environment Variables
### Required
- `DATABASE_URL` - PostgreSQL connection string
- `INTERNAL_API_KEY` - API key for mutating endpoints
- `SCRAPER_API_KEY` (aliases: `SCRAPPER_API`, `SCRAPPPER_API`)
- `OPENAI_API_KEY` - OpenAI API key
- `REDIS_URL` - Redis connection (default: `redis://localhost:6379/0`)

### Optional
- `PRICE_MONITOR_EXECUTOR` (celery|local, default: celery)
- `PROXY_PROVIDER` (auto|scraperapi|brightdata|direct, default: auto)
- `CORS_ALLOWED_ORIGINS` - Comma-separated origins
- `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10`, `DB_POOL_TIMEOUT_SECONDS=30`, `DB_POOL_RECYCLE_SECONDS=180`
- `BRIGHT_DATA_ACCOUNT_ID`, `BRIGHT_DATA_ZONE_NAME`, `BRIGHT_DATA_ZONE_PASSWORD`
- `VITE_QUERY_CACHE_TTL_MS=45000`, `VITE_INTERNAL_API_KEY`

## Recent Changes
- 2025-02-19: Cleaned up outdated planning/architecture documentation files
- 2025-02-19: Created comprehensive project documentation (README.md, ARCHITECTURE.md, backend/README.md, frontend/README.md)
