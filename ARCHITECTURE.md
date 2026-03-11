# Architecture Reference (Updated: 2026-02-24)

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React 19 + TypeScript + Vite 7 + TailwindCSS v4             │
│  Port 5173 (dev) / Static build served by backend            │
│                                                              │
│  14 Page Components (lazy-loaded):                            │
│  Dashboard, Products, ProductDetail, Ads, PriceMonitor,       │
│  Sellers, SellerDetail, UrlScraper, VideoTranscripts,         │
│  JsonEditor, HepsiburadaProducts, TrendyolProducts,           │
│  WebProducts, CategoryExplorer                                │
└──────────────────┬───────────────────────────────────────────┘
                   │ HTTP (axios → /api/*)
                   ▼
┌──────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                         │
│                     Port 8000                                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ routes.py (barrel module, re-exports from):             │  │
│  │   search_routes.py    product_routes.py                 │  │
│  │   stats_routes.py     price_monitor_routes.py           │  │
│  │   seller_routes.py    _shared.py (Pydantic models)      │  │
│  └──────────────────────────┬─────────────────────────────┘  │
│                             │                                │
│  ┌──────────────┐ ┌────────────────────┐ ┌───────────────┐  │
│  │ url_scraper_ │ │ store_product_     │ │ transcript_   │  │
│  │ routes.py    │ │ routes.py          │ │ routes.py     │  │
│  └──────┬───────┘ └────────┬───────────┘ └──────┬────────┘  │
│  ┌──────────────┐ ┌────────────────────┐ ┌───────────────┐  │
│  │ category_    │ │ json_editor_       │ │               │  │
│  │ explorer_    │ │ routes.py          │ │  (mounted in  │  │
│  │ routes.py    │ │                    │ │   main.py)    │  │
│  └──────┬───────┘ └────────┬───────────┘ └──────┬────────┘  │
│         │                  │                     │           │
│  ┌──────┴──────────────────┴─────────────────────┴────────┐  │
│  │                    SERVICES                             │  │
│  │  scraping.py          price_monitor_service.py          │  │
│  │  proxy_providers.py   trendyol_price_monitor_service.py │  │
│  │  llm_service.py       url_scraper_service.py            │  │
│  │  transcript_service.py  category_scraper_service.py     │  │
│  └────────────┬──────────────────────┬─────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  CORE: url_validator.py (SSRF protection)              │   │
│  └────────────────────────────────────────────────────────┘   │
│               │                      │                        │
│  ┌────────────▼──────┐   ┌──────────▼──────────┐            │
│  │  Proxy System     │   │  Celery Tasks       │            │
│  │  ScraperAPI (1st) │   │  tasks.py           │            │
│  │  Direct (2nd)     │   │  broker: Redis      │            │
│  │                   │   │  backend: Redis     │            │
│  └───────────────────┘   └──────────┬──────────┘            │
└──────────────────────────────────────┼───────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────┐
              ▼                        ▼                    ▼
    ┌──────────────┐         ┌──────────────┐     ┌──────────────┐
    │  PostgreSQL   │         │    Redis      │     │ External APIs│
    │  (Neon)       │         │  Queue/Cache  │     │ ScraperAPI   │
    │  18 tables    │         │              │     │ OpenAI       │
    │              │         │              │     │ YouTube API  │
    └──────────────┘         └──────────────┘     │              │
                                                   └──────────────┘
```

## Database Schema

### Core Product Tables

```
products
├── id: UUID (PK)
├── platform: VARCHAR(20)        # hepsiburada, trendyol
├── external_id: TEXT
├── sku: VARCHAR(100)
├── barcode: VARCHAR(50)
├── name: TEXT
├── url: TEXT
├── brand: VARCHAR(255)
├── seller_name: VARCHAR(255)
├── seller_rating: FLOAT
├── category_path: TEXT
├── category_hierarchy: TEXT
├── image_url: TEXT
├── description: TEXT
├── origin_country: VARCHAR(100)
├── created_at: TIMESTAMP
├── updated_at: TIMESTAMP
│
├──► product_snapshots (1:N)     # Daily price/rating snapshots
│    ├── price, discounted_price, discount_percentage
│    ├── rating, reviews_count
│    ├── stock_count, in_stock, is_sponsored
│    ├── coupons: JSON, campaigns: JSON
│    └── snapshot_date: DATE
│
├──► product_sellers (1:N)       # Other sellers for same product
│    ├── seller_name, seller_rating, price
│    ├── is_authorized, shipping_info
│    └── snapshot_date: DATE
│
└──► product_reviews (1:N)       # Customer reviews
     ├── author, rating, review_text
     ├── review_date, seller_name
     └── is_helpful_count
```

### Search & Ads Tables

```
search_tasks
├── id: UUID (PK)
├── keyword, platform, status
├── total_products, total_sponsored_products
├── created_at, completed_at, error_message
│
├──► sponsored_brand_ads (1:N)   # Brand carousel ads
│    ├── seller_name, seller_id, position
│    ├── products: JSON
│    └── snapshot_date: DATE
│
└──► search_sponsored_products (1:N)  # Individual sponsored products
     ├── order_index, product_url, product_name
     ├── seller_name, price, discounted_price
     ├── image_url, payload: JSON
     └── snapshot_date: DATE
```

### Price Monitor Tables

```
monitored_products
├── id: UUID (PK)
├── platform: VARCHAR(20)        # hepsiburada, trendyol
├── sku, barcode, product_url, product_name
├── brand, seller_stock_code
├── threshold_price              # Alert threshold (original_price)
├── alert_campaign_price         # Alert threshold (campaign price)
├── image_url, is_active
├── created_at, updated_at, last_fetched_at
│
└──► seller_snapshots (1:N)      # Per-seller price data
     ├── merchant_id, merchant_name, merchant_logo
     ├── merchant_url_postfix, merchant_rating, merchant_rating_count, merchant_city
     ├── price, original_price, minimum_price, discount_rate
     ├── stock_quantity, buybox_order
     ├── free_shipping, fast_shipping, is_fulfilled_by_hb
     ├── delivery_info, campaign_info
     ├── campaigns: JSON, campaign_price
     └── snapshot_date: TIMESTAMP

price_monitor_tasks
├── id: UUID (PK)
├── platform, status, stop_requested
├── total_products, completed_products, failed_products
├── created_at, completed_at, error_message
├── last_inactive_skus: JSON
├── last_processed_index
└── fetch_type: VARCHAR(20)      # active, last_inactive, inactive
```

### Utility Tables

```
scrape_jobs                      # URL scraper jobs
├── id: UUID (PK)
├── status, total_urls, completed_urls, failed_urls
└──► scrape_results (1:N)
     ├── url, product_name, barcode
     ├── status, scraped_data: JSON, error_message

transcript_jobs                  # YouTube transcript jobs
├── id: UUID (PK)
├── status, total_videos, completed_videos, failed_videos
└──► transcript_results (1:N)
     ├── video_url, product_name, barcode
     ├── language, language_code, is_generated
     ├── transcript_text, transcript_snippets: JSON

json_files                       # JSON editor storage
├── id: UUID (PK)
├── filename, json_content: JSON
├── created_at, updated_at
```

### Store & Category Tables

```
store_products                   # Marketplace ürün verileri (Hepsiburada, Trendyol, Web)
├── id: UUID (PK)
├── platform, product_url, title, brand
├── price, original_price, currency
├── seller_name, seller_url
├── rating, review_count
├── image_url, category
├── attributes: JSON
├── source_type
├── scraped_at, created_at

category_sessions                # Kategori tarama oturumlari
├── id: UUID (PK)
├── name, platform, category_url
├── status
├── total_products
├── created_at, updated_at

category_products                # Kategori ürün verileri
├── id: UUID (PK)
├── session_id: UUID (FK → category_sessions)
├── product_url, title, brand, seller_name
├── sku, barcode
├── price, original_price
├── image_url, rating, review_count
├── stock_status, shipping_type
├── category_path, description
├── specs: JSON, seller_list: JSON, detail_data: JSON
├── detail_fetched
├── created_at
```

## API Endpoints

### Main Routes (`/api/*`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/search` | Start keyword search task |
| GET | `/api/search/{task_id}` | Get search task status |
| GET | `/api/tasks` | List all search tasks |
| GET | `/api/search/{task_id}/sponsored-brands` | Get brand ads for search |
| GET | `/api/search/{task_id}/sponsored-products` | Get sponsored products for search |
| GET | `/api/products` | List products (filterable) |
| GET | `/api/products/{id}` | Get product detail |
| GET | `/api/products/{id}/snapshots` | Get price/rating history |
| POST | `/api/analyze` | AI analysis of products |
| GET | `/api/stats` | Dashboard statistics |
| GET | `/api/scraping/status` | Proxy and scraping status |

### Price Monitor (`/api/price-monitor/*`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/price-monitor/products` | Add monitored products (bulk) |
| GET | `/api/price-monitor/products` | List monitored products |
| GET | `/api/price-monitor/products/{id}` | Product detail with seller snapshots |
| DELETE | `/api/price-monitor/products/{id}` | Delete monitored product |
| DELETE | `/api/price-monitor/products/bulk/all` | Delete all products |
| DELETE | `/api/price-monitor/products/bulk/inactive` | Delete inactive products |
| POST | `/api/price-monitor/fetch` | Start price fetch task |
| POST | `/api/price-monitor/fetch/{id}/stop` | Stop running fetch |
| GET | `/api/price-monitor/fetch/{id}` | Fetch task status |
| POST | `/api/price-monitor/fetch-single/{id}` | Fetch single product |
| GET | `/api/price-monitor/last-inactive` | Get last inactive SKUs |
| GET | `/api/price-monitor/brands` | List monitored brands |
| GET | `/api/price-monitor/export` | Export data as CSV |

### Sellers (`/api/sellers/*`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sellers` | List sellers with aggregated data |
| GET | `/api/sellers/{merchant_id}/products` | Seller's products |
| GET | `/api/sellers/{merchant_id}/export` | Export seller data as CSV |

### URL Scraper (`/api/url-scraper/*`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/url-scraper/scrape` | Scrape single URL |
| POST | `/api/url-scraper/scrape-bulk` | Scrape bulk URLs (JSON) |
| POST | `/api/url-scraper/scrape-csv` | Scrape URLs from CSV |
| GET | `/api/url-scraper/jobs` | List scrape jobs |
| GET | `/api/url-scraper/jobs/{id}` | Job status and results |
| GET | `/api/url-scraper/jobs/{id}/download` | Download results as JSON |
| DELETE | `/api/url-scraper/jobs/{id}` | Delete job |
| POST | `/api/url-scraper/jobs/{id}/stop` | Stop running job |

### Transcripts (`/api/transcripts/*`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/transcripts/fetch` | Fetch single transcript |
| POST | `/api/transcripts/fetch-bulk` | Fetch bulk transcripts |
| POST | `/api/transcripts/fetch-csv` | Fetch from CSV |
| GET | `/api/transcripts/jobs` | List transcript jobs |
| GET | `/api/transcripts/jobs/{id}` | Job status and results |
| GET | `/api/transcripts/jobs/{id}/download` | Download results |
| DELETE | `/api/transcripts/jobs/{id}` | Delete job |
| POST | `/api/transcripts/jobs/{id}/stop` | Stop running job |

### JSON Editor (`/api/json-editor/*`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/json-editor/files` | List JSON files |
| POST | `/api/json-editor/files` | Create/upload JSON file |
| GET | `/api/json-editor/files/{id}` | Get file content |
| PUT | `/api/json-editor/files/{id}` | Update file content |
| DELETE | `/api/json-editor/files/{id}` | Delete file |
| DELETE | `/api/json-editor/files` | Delete all files |

### Store Products (`/api/store-products/*`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/store-products/` | Ürün listesi (filtreleme, sayfalama) |
| GET | `/api/store-products/categories` | Kategori agaci |
| GET | `/api/store-products/{id}` | Ürün detay |
| POST | `/api/store-products/scrape-from-urls` | URL'lerden ürün çek |
| POST | `/api/store-products/scrape-from-monitor` | Monitor'dan ürün çek |
| POST | `/api/store-products/import-excel` | Excel'den import |
| DELETE | `/api/store-products/{id}` | Ürün sil |
| POST | `/api/store-products/backfill-prices` | Fiyat gecmisi doldur |

### Category Explorer (`/api/category-explorer/*`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/category-explorer/scrape-page` | Kategori sayfasi tara |
| GET | `/api/category-explorer/sessions` | Oturum listesi |
| GET | `/api/category-explorer/sessions/{id}` | Oturum detay |
| DELETE | `/api/category-explorer/sessions/{id}` | Oturum sil |
| POST | `/api/category-explorer/fetch-detail` | Tekil ürün detay çek |
| POST | `/api/category-explorer/bulk-fetch` | Toplu detay çek |
| GET | `/api/category-explorer/category-filters` | Kategori filtreleri |
| GET | `/api/category-explorer/products-by-category` | Kategoriye göre ürünler |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health check |

## Proxy System

The proxy system uses a fallback chain for reliable scraping:

```
Request → ScraperAPI (cheap, render=true)
              │
              ├── Success → Return data
              │
              └── Fail → Direct connection (last resort)
```

Configuration via `PROXY_PROVIDER` env var:
- `auto` (default): ScraperAPI → Direct
- `scraperapi`: ScraperAPI only
- `direct`: No proxy

## Celery Tasks

| Task | Description |
|------|-------------|
| `run_scraping_task` | Execute keyword search and save products |
| `run_price_monitor_fetch_task` | Fetch prices for monitored products (Hepsiburada or Trendyol) |

Celery uses Redis as both broker and result backend. Configure via `REDIS_URL`.

## Data Flow

### Keyword Search
1. User submits keyword → `POST /api/search`
2. FastAPI creates `SearchTask` (status: pending) → returns task ID
3. Background task runs scraping via Playwright + proxy
4. Products saved to `products` + `product_snapshots`
5. Sponsored ads saved to `sponsored_brand_ads` + `search_sponsored_products`
6. Task status updated to completed

### Price Monitor Fetch
1. User triggers fetch → `POST /api/price-monitor/fetch`
2. Task created in `price_monitor_tasks`
3. Celery task processes each `MonitoredProduct`:
   - Calls marketplace API for seller data
   - Saves `SellerSnapshot` per merchant
   - Tracks inactive/failed SKUs
4. Supports stop/resume via `stop_requested` flag

### URL Scraping
1. User submits URLs → `POST /api/url-scraper/scrape-bulk`
2. `ScrapeJob` created, URLs queued as `ScrapeResult` (status: pending)
3. Background workers (40 concurrent) fetch each URL via ScraperAPI
4. Extract data via meta tags, JSON-LD, Open Graph, HTML parsing
5. Results downloadable as JSON
