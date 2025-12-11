# Pazaryeri Veri Analiz Platformu

## Overview
A Marketplace Data Analysis Platform that helps marketplace sellers and marketing agencies make data-driven decisions. The platform scrapes product data from Turkish marketplaces (starting with Hepsiburada), analyzes trends, and provides AI-powered insights.

## Current State
- **Status**: MVP Phase 2 - Enhanced Data Collection
- **Backend**: FastAPI with PostgreSQL, BackgroundTasks for async scraping
- **Frontend**: React + Vite + TailwindCSS v4
- **Features**: Product search, two-stage scraping, rich product data, price/rating charts, AI analysis
- **Note**: Using FastAPI BackgroundTasks instead of Celery/Redis for simplicity in MVP

## Scraping Strategy
**Two-Stage Scraping Approach:**
1. **Stage 1**: Get product URLs from search/listing page
2. **Stage 2**: Visit each product detail page to extract comprehensive data

**Data Sources from Product Detail Pages:**
- `utagData` JavaScript object: product name, brand, category hierarchy, price, SKU, barcode, seller name, rating, review count, stock status
- JSON-LD Schema: aggregateRating, brand, description, image
- HTML elements: discounted price, coupons, campaigns, other sellers, reviews, stock count, origin country

**Limits:**
- MAX_PRODUCTS_PER_SEARCH = 8 (to manage Bright Data costs)

## Project Structure
```
.
├── backend/
│   ├── app/
│   │   ├── api/routes.py         # API endpoints
│   │   ├── core/config.py        # Configuration
│   │   ├── db/
│   │   │   ├── database.py       # SQLAlchemy setup
│   │   │   └── models.py         # Product, Snapshot, Seller, Review models
│   │   ├── services/
│   │   │   ├── scraping.py       # Two-stage Playwright + Bright Data scraping
│   │   │   └── llm_service.py    # OpenAI integration
│   │   └── main.py               # FastAPI app entry
│   ├── run.py                    # Backend runner
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/Layout.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx     # Main dashboard with search
│   │   │   ├── Products.tsx      # Product list
│   │   │   └── ProductDetail.tsx # Product details with tabs (info, sellers, reviews)
│   │   └── services/api.ts       # API client with extended types
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
- `BRIGHT_DATA_ACCOUNT_ID` - Bright Data account ID (e.g., hl_xxxxx)
- `BRIGHT_DATA_ZONE_NAME` - Bright Data Residential Proxy zone name
- `BRIGHT_DATA_ZONE_PASSWORD` - Bright Data zone password

## Tech Stack
- **Frontend**: React 18, TypeScript, TailwindCSS v4, Plotly.js, React Router
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, BackgroundTasks
- **Scraping**: Playwright, playwright-stealth, BeautifulSoup4, Bright Data Residential Proxy
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

## User Preferences
- Turkish language UI
- Focus on Hepsiburada marketplace initially
- Limit to 8 products per search to manage costs

## Recent Changes
- December 11, 2025: Phase 2 - Enhanced Data Collection
  - Two-stage scraping: URL collection + product detail page scraping
  - utagData parser: extracts rich data from JavaScript object
  - JSON-LD parser: extracts structured data
  - HTML parser: extracts discounted prices, coupons, campaigns, other sellers
  - Extended database schema: new columns and tables for sellers/reviews
  - ProductDetail page: tabs for info, other sellers, reviews display
  - Frontend updated with new data types and UI components
- December 10, 2025: Bright Data Residential Proxies integration
  - chromium.launch(proxy=config) for Hepsiburada scraping
  - playwright-stealth for bot detection bypass
- December 10, 2025: Initial MVP implementation
