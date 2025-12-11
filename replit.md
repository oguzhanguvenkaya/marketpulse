# Pazaryeri Veri Analiz Platformu

## Overview
A Marketplace Data Analysis Platform that helps marketplace sellers and marketing agencies make data-driven decisions. The platform scrapes product data from Turkish marketplaces (starting with Hepsiburada), analyzes trends, and provides AI-powered insights.

## Current State
- **Status**: MVP Phase 2.5 - Modular Proxy Architecture
- **Backend**: FastAPI with PostgreSQL, BackgroundTasks for async scraping
- **Frontend**: React + Vite + TailwindCSS v4
- **Features**: Product search, two-stage scraping, rich product data, price/rating charts, AI analysis
- **Proxy System**: Modular multi-provider (ScraperAPI + Bright Data with auto-fallback)

## Proxy Architecture

### Provider Hierarchy (Auto Mode)
1. **ScraperAPI** (Primary) - Ucuz, 3M istek/ay $249, PROXY PORT metodu ile
2. **Bright Data** (Fallback) - Premium, Playwright proxy ile
3. **Direct** (Last resort) - Proxy yok

### Implementation Details - WORKING METHOD
- **ScraperAPI**: **PROXY PORT** metodu kullanılır (HTTP API bot kontrolünü geçemiyor)
  - Proxy URL: `http://proxy-server.scraperapi.com:8001`
  - Username: `scraperapi.output_format=json.autoparse=true.country_code=tr.device_type=desktop.max_cost=200.session_number={random}`
  - Password: API Key
  - aiohttp ile async istek, proxy üzerinden
  - BeautifulSoup ile HTML parse
- **Bright Data**: Playwright proxy olarak kullanılır (fallback)

### Configuration
```python
PROXY_PROVIDER = "auto"  # Options: auto, scraperapi, brightdata
DEBUG_SAVE_HTML = true   # Save HTML on errors for debugging
```

### Fallback Logic
- If ScraperAPI PROXY returns homepage/error -> Auto-switch to Bright Data
- Debug HTML saved to `/tmp/scraping_debug/` for analysis

## Scraping Strategy
**Two-Stage Scraping Approach:**
1. **Stage 1**: Get product URLs from search/listing page
2. **Stage 2**: Visit each product detail page to extract comprehensive data

**Data Sources from Product Detail Pages:**
- `utagData` JavaScript object: product name, brand, category hierarchy, price, SKU, barcode, seller name, rating, review count, stock status
- JSON-LD Schema: aggregateRating, brand, description, image
- HTML elements: discounted price, coupons, campaigns, other sellers, reviews, stock count, origin country

**Limits:**
- MAX_PRODUCTS_PER_SEARCH = 8 (to manage proxy costs)

## Project Structure
```
.
├── backend/
│   ├── app/
│   │   ├── api/routes.py           # API endpoints
│   │   ├── core/config.py          # Configuration (proxy settings)
│   │   ├── db/
│   │   │   ├── database.py         # SQLAlchemy setup
│   │   │   └── models.py           # Product, Snapshot, Seller, Review models
│   │   ├── services/
│   │   │   ├── scraping.py         # Two-stage Playwright scraping
│   │   │   ├── proxy_providers.py  # Modular proxy provider system
│   │   │   └── llm_service.py      # OpenAI integration
│   │   └── main.py                 # FastAPI app entry
│   ├── run.py                      # Backend runner
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/Layout.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # Main dashboard with search
│   │   │   ├── Products.tsx        # Product list
│   │   │   └── ProductDetail.tsx   # Product details with tabs
│   │   └── services/api.ts         # API client with extended types
│   ├── package.json
│   └── vite.config.ts
└── replit.md
```

## Database Schema

### Products Table
- id, platform, external_id, sku, barcode, name, url
- brand, seller_name, seller_rating
- category_path, category_hierarchy
- image_url, description, origin_country
- created_at, updated_at

### ProductSnapshots Table
- id, product_id, snapshot_date
- price, discounted_price, discount_percentage
- rating, reviews_count, stock_count, in_stock
- is_sponsored, coupons (JSON), campaigns (JSON)

### ProductSellers Table
- id, product_id, seller_name, seller_rating
- price, is_authorized, shipping_info, snapshot_date

### ProductReviews Table
- id, product_id, author, rating, review_text
- review_date, seller_name, is_helpful_count

## Running the Project
- **Frontend**: Runs on port 5000 (webview)
- **Backend**: Runs on port 8000 (localhost)

## Environment Variables Required
- `DATABASE_URL` - PostgreSQL connection (auto-configured by Replit)
- `OPENAI_API_KEY` - For AI analysis features
- `SCRAPPER_API` - ScraperAPI key (primary proxy)
- `BRIGHT_DATA_ACCOUNT_ID` - Bright Data account ID (fallback)
- `BRIGHT_DATA_ZONE_NAME` - Bright Data Residential Proxy zone name
- `BRIGHT_DATA_ZONE_PASSWORD` - Bright Data zone password
- `PROXY_PROVIDER` - Provider selection: auto, scraperapi, brightdata (default: auto)

## Tech Stack
- **Frontend**: React 18, TypeScript, TailwindCSS v4, Plotly.js, React Router
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, BackgroundTasks
- **Scraping**: Playwright, playwright-stealth, BeautifulSoup4
- **Proxy**: ScraperAPI (primary), Bright Data Residential (fallback)
- **Database**: PostgreSQL (Replit built-in)
- **AI**: OpenAI GPT-4o-mini

## API Endpoints
- `POST /api/search` - Start a new search task (scrapes up to 8 products)
- `GET /api/search/{id}` - Get task status
- `GET /api/tasks` - List recent tasks
- `GET /api/products` - List products with latest snapshot data
- `GET /api/products/{id}` - Get product details including other sellers and reviews
- `GET /api/products/{id}/snapshots` - Get price/rating history
- `POST /api/analyze` - AI analysis of products
- `GET /api/stats` - Dashboard statistics
- `GET /api/scraping/status` - Proxy provider status and availability

## User Preferences
- Turkish language UI
- Focus on Hepsiburada marketplace initially
- Limit to 8 products per search to manage costs
- ScraperAPI as primary (cheaper), Bright Data for fallback

## Recent Changes
- December 11, 2025: Phase 2.5 - Modular Proxy Architecture
  - Added ScraperAPI as primary proxy provider (cheaper)
  - Bright Data moved to fallback role
  - ProxyManager class with auto-fallback logic
  - DebugLogger for detailed error tracking
  - Debug HTML saving on 403/429/503 errors
  - /api/scraping/status endpoint for monitoring
- December 11, 2025: Phase 2 - Enhanced Data Collection
  - Two-stage scraping: URL collection + product detail page scraping
  - utagData parser: extracts rich data from JavaScript object
  - JSON-LD parser: extracts structured data
  - HTML parser: extracts discounted prices, coupons, campaigns, other sellers
  - Extended database schema: new columns and tables for sellers/reviews
- December 10, 2025: Bright Data Residential Proxies integration
- December 10, 2025: Initial MVP implementation
