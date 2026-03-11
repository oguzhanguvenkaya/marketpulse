# Pazaryeri Veri Analiz Platformu (MarketPulse)

## Overview
The Marketplace Data Analysis Platform empowers marketplace sellers and marketing agencies with data-driven decision-making capabilities. It scrapes product data from major Turkish marketplaces (Hepsiburada, Trendyol), analyzes market trends, tracks seller prices, monitors sponsored ads, and delivers AI-powered insights. The platform serves as a tool for competitive analysis, strategic pricing, and understanding market dynamics within the e-commerce landscape.

## User Preferences
- English language UI with Palantir-style dark theme
- Focus on Hepsiburada marketplace initially, Trendyol support added for price monitoring
- Limit to 8 products per search to manage costs
- ScraperAPI as primary proxy provider, direct connection as fallback

## UI Theme (Honey)
- Light warm color palette: Background #fffbef, Card #fefbf0, Muted #f7eede, Border #e5e0d2
- Primary accent: Dark brown (#5b4824), Secondary accent: Honey gold (#f7ce86), Tertiary: Sage (#e6ecd3)
- Text colors: Primary #0f1419, Secondary #5f471d, Muted #9e8b66, Subtle #b5a382
- Status colors: Success green (#22c55e), Warning orange (#f59e0b), Danger red (#cb5150)
- Typography: Inter (body), Lora (headings), Space Grotesk (monospace)
- Border radius: 0.875rem (14px) for cards and buttons
- Reusable components: card-dark, btn-primary/secondary, input-dark, table-dark, badges, stat-card
- Subtle animations: fade-in, slide-in, pulse-glow effects
- Chart colors: #1e9df1, #00b87a, #f7b928, #17bf63, #e6245e

## System Architecture
The platform is built with a clear separation of concerns, featuring a FastAPI backend (port 8000) and a React frontend (port 5173 dev / static served by backend in production). It employs a robust, two-stage scraping strategy for comprehensive data collection and a modular proxy architecture for reliable data acquisition. Celery + Redis handle async task execution for price monitoring and search jobs.

### Backend Structure
```
backend/app/
├── api/           → Route handlers: routes.py (barrel re-export), _shared.py (Pydantic models),
│                    search_routes.py, product_routes.py, stats_routes.py, seller_routes.py,
│                    price_monitor_routes.py, store_product_routes.py, category_explorer_routes.py,
│                    url_scraper_routes.py, transcript_routes.py, json_editor_routes.py
├── core/          → config.py (Settings), security.py (API key auth), logger.py, url_validator.py (SSRF protection)
├── db/            → database.py (SQLAlchemy engine), models.py (13 ORM models)
├── services/      → scraping.py, price_monitor_service.py, trendyol_price_monitor_service.py,
│                    proxy_providers.py, llm_service.py, url_scraper_service.py, transcript_service.py,
│                    category_scraper_service.py
├── tasks.py       → Celery app + task definitions (run_scraping_task, run_price_monitor_fetch_task)
└── main.py        → FastAPI app init, CORS, health endpoint, SPA serving
```

### Frontend Structure
```
frontend/src/
├── pages/         → 14 lazy-loaded pages (Dashboard, Products, ProductDetail, Ads, PriceMonitor,
│                    Sellers, SellerDetail, HepsiburadaProducts, TrendyolProducts, WebProducts,
│                    CategoryExplorer, UrlScraper, VideoTranscripts, JsonEditor)
├── hooks/         → useCategoryExplorer.ts, usePriceMonitor.ts
├── components/    → ApiKeyModal, ConfirmDialog, ErrorBoundary, Layout, MarketplaceProductList,
│                    Skeleton, Sparkline + sub-component dirs: category-explorer/, price-monitor/
├── services/      → api.ts (12-line barrel re-export), client.ts (Axios instance + interceptors),
│                    types.ts (interfaces), searchApi.ts, productApi.ts, statsApi.ts,
│                    priceMonitorApi.ts, sellerApi.ts, scrapeApi.ts, transcriptApi.ts,
│                    storeProductApi.ts, categoryApi.ts, queryCache.ts (TTL-based cache)
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
Features an "auto" mode that prioritizes ScraperAPI and falls back to direct connection. Includes debug logging and HTML saving to `/tmp/scraping_debug/` for troubleshooting.

### URL Scraper
Generic URL scraping system. Supports single URL, bulk JSON, and CSV upload. Uses ScraperAPI to fetch pages, extracts data via meta tags, JSON-LD, Open Graph, and HTML parsing. 40 concurrent workers with stop/resume. DB models: `ScrapeJob`, `ScrapeResult`. Routes: `/api/url-scraper/`.

### YouTube Video Transcript Scraper
Extracts transcripts using `youtube-transcript-api`. Supports single URL, bulk JSON, and CSV upload (auto-detects Video_URL columns). 40 concurrent workers with stop/resume. DB models: `TranscriptJob`, `TranscriptResult`. Routes: `/api/transcripts/`. Frontend: `/video-transcripts`.

### JSON Product Editor
Full-stack tool for editing product catalog JSON files with PostgreSQL persistence. Fully dynamic rendering: all product keys auto-detected and rendered based on value type. Supports any JSON structure. DB model: `JsonFile`. Routes: `/api/json-editor/`. Frontend: `/json-editor`.

### Marketplace Product Pages
Three dedicated pages (Hepsiburada, Trendyol, Web) displaying scraped product data with advanced filtering. Uses `StoreProduct` table populated from URL scraper results. Supports filtering by category, brand, price range, rating, SKU, barcode. Product detail modal shows breadcrumb categories, reviews, specs, shipping info. "Scrape Products" button triggers bulk scraping from active price monitor products. Routes: `/api/store-products/`. Frontend: `/hepsiburada`, `/trendyol`, `/web-products`.

### Category Explorer
Competitive analysis tool to scrape and browse marketplace category pages. Paste a Hepsiburada or Trendyol category URL to view all product listings, breadcrumb navigation, filter by brand/price/sponsored status, and fetch detailed product data for each item. Two-step scraping: category page listing data first, then individual product detail on demand. Supports pagination via platform-specific parameters (sayfa for HB, pi for Trendyol). DB models: `CategorySession`, `CategoryProduct`. Routes: `/api/category-explorer/`. Frontend: `/category-explorer`.

## Database Models (18 tables)
- `Product`, `ProductSnapshot`, `ProductSeller`, `ProductReview`
- `SearchTask`, `SponsoredBrandAd`, `SearchSponsoredProduct`
- `MonitoredProduct`, `SellerSnapshot`, `PriceMonitorTask`
- `ScrapeJob`, `ScrapeResult`
- `StoreProduct`
- `TranscriptJob`, `TranscriptResult`
- `CategorySession`, `CategoryProduct`
- `JsonFile`

## Key API Route Groups
- `/api/search`, `/api/products`, `/api/stats` → Main search and product routes
- `/api/price-monitor/*` → Price monitoring (products, fetch, sellers, export)
- `/api/sellers/*` → Seller analysis and export
- `/api/url-scraper/*` → URL scraping jobs
- `/api/transcripts/*` → YouTube transcript jobs
- `/api/json-editor/*` → JSON file management
- `/api/category-explorer/*` → Category page scraping and competitive analysis
- `/health` → System health check

## Celery Tasks (Lazy Initialization)
- `run_scraping_task`: Execute keyword search via Playwright and save products
- `run_price_monitor_fetch_task`: Fetch prices for monitored products (Hepsiburada or Trendyol)
- Broker/Backend: Redis (`REDIS_URL`) - only initialized when first task is dispatched
- Celery app created lazily via `get_celery_app()` to avoid blocking app startup
- Production uses `PRICE_MONITOR_EXECUTOR=local` (no Redis needed for autoscale)
- Development can use either `celery` or `local` executor

## External Dependencies
- **Database:** PostgreSQL (Neon-backed on Replit)
- **Queue:** Redis (Celery broker/backend) - optional, only needed when PRICE_MONITOR_EXECUTOR=celery
- **AI Service:** OpenAI (GPT-4o-mini)
- **Proxy Services:**
    - ScraperAPI (Primary, cost-effective)
    - Direct connection (Fallback)
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
- `PROXY_PROVIDER` (auto|scraperapi|direct, default: auto)
- `CORS_ALLOWED_ORIGINS` - Comma-separated origins
- `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10`, `DB_POOL_TIMEOUT_SECONDS=30`, `DB_POOL_RECYCLE_SECONDS=180`

- `VITE_QUERY_CACHE_TTL_MS=45000`

## Recent Changes
- 2026-02-22: Deployment fix: Lazy Celery/Redis initialization to prevent autoscale timeout. Database engine lazy via proxy classes. CORS auto-includes REPLIT_DOMAINS. Production uses PRICE_MONITOR_EXECUTOR=local. Deploy target changed from cloudrun to autoscale
- 2026-02-22: Theme change: Switched from Palantir dark theme to Honey light theme. Updated CSS variables, Tailwind config, Layout, and all 14 pages. Colors: cream backgrounds (#fffbef), dark brown primary (#5b4824), honey gold accent (#f7ce86). Typography: Inter body, Lora headings, Space Grotesk monospace. Chart colors updated to Honey palette
- 2026-02-22: Hybrid detail fetch: Listings API (sellers/prices/stock/buybox/campaigns as clean JSON) + HTML (brand/description/specs via utagData) in parallel. SKU extracted from product URLs (pm-HBCXXXXX pattern) during category scrape. Removed dead _extract_hb_product_data_from_scripts(). Deferred Listings API call when SKU discovered from HTML. Price hierarchy: Listings API buybox #1 > utagData > parsed
- 2026-02-22: Enhanced detail fetch: utagData parsing for brand, seller_list, SKU, barcode, category_path, stock_status, shipping_type, specs, description. New DB columns on CategoryProduct. Price fix: CSS class-based extraction (originalPrice/currentPrice/discountRate) replacing regex that captured campaign text. Duplicate handling: URL-based dedup with UPDATE on re-scrape. Sponsored ad URL resolution via redirect param. Frontend detail panel shows all new fields
- 2026-02-22: Marketplace sidebar filter extraction: HB VerticalFilter brand links (19 brands), Satıcı facet script data with €XX→%XX URL decode (18 sellers), price ranges from Fiyat Aralığı. TY filters from __SEARCH_APP_INITIAL_STATE__. filter_data JSON column on CategorySession. category-filters endpoint merges marketplace + product-derived filters. Frontend instantly populates filter dropdowns from session.filter_data after scrape
- 2026-02-22: Category Page filters: brand/seller/price range/rating/sponsored filters for scraped category products. Brand extraction from HB product cards (h2 vs a[title] diff). New /category-filters endpoint. Stats bar shows brand_count, seller_count, last_scraped. Sort options separated per view mode
- 2026-02-22: Category Explorer redesign: multi-page scraping (page_count 1-20, HB ?sayfa=N / TY ?pi=N), "Get Product Details" panel with checkbox selection + Select All, bulk detail fetch with polling progress, cyan/purple visual separation for scrape vs detail operations
- 2026-02-22: Collapsible sidebar: desktop toggle to collapse/expand sidebar (icon-only vs full labels), state persisted in localStorage, all pages auto-adjust. Mobile drawer behavior unchanged
- 2026-02-22: Category URL auto-fill v2: category-tree endpoint now extracts marketplace category URLs from store_products raw_scraped_data breadcrumb JSON-LD. Each sidebar category node carries its permanent URL (100% HB, 85% TY coverage). Selecting a category instantly populates scrape URL without any fuzzy matching or external lookup
- 2026-02-22: Added Category Explorer for competitive analysis: scrape HB/Trendyol category pages, view product listings with breadcrumb navigation, filter by brand/price/sponsored, bulk fetch product details. DB models: CategorySession, CategoryProduct. Routes: /api/category-explorer/. Frontend: /category-explorer
- 2026-02-22: Added Excel import for web products (POST /api/store-products/import-excel), improved price extraction with multi-source fallback, redesigned product detail as slide-in side panel
- 2026-02-22: Increased all concurrent workers to 40 (URL scraper, transcript, price monitor HB+TY)
- 2026-02-22: Added geotargeting to all ScraperAPI methods: TR domains→country_code=eu, others→US/EU random
- 2026-02-22: Added Marketplace Product Pages (Hepsiburada, Trendyol, Web) with StoreProduct model, advanced filtering, category breadcrumb extraction
- 2026-02-22: Enhanced URL scraper: WebPage JSON-LD breadcrumb parsing, Trendyol SEO props parsing, reviews/shipping/return policy extraction
- 2025-02-19: Cleaned up outdated planning/architecture documentation files
- 2025-02-19: Created comprehensive project documentation (README.md, ARCHITECTURE.md, backend/README.md, frontend/README.md)
