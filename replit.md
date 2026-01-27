# Pazaryeri Veri Analiz Platformu

## Overview

This is a marketplace data analysis platform designed to scrape, monitor, and analyze product data from Turkish e-commerce platforms (Hepsiburada and Trendyol). The platform collects product information, tracks price changes across multiple sellers, monitors sponsored products/ads, and provides AI-powered analysis using OpenAI's GPT models.

Key capabilities:
- Web scraping of product listings and search results
- Price monitoring across multiple sellers
- Sponsored product and brand ad tracking
- LLM-powered market analysis and recommendations
- Historical price and snapshot tracking

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite 7
- **Styling**: Tailwind CSS 4 with custom dark theme
- **Routing**: React Router DOM 7
- **Data Visualization**: Plotly.js with react-plotly.js wrapper
- **HTTP Client**: Axios
- **Development Server**: Runs on port 5000 with API proxy to backend

The frontend follows a standard SPA pattern with:
- Layout component for consistent navigation
- Page-based routing (Dashboard, Products, Ads, PriceMonitor, Sellers)
- Custom dark theme with cyan accent colors

### Backend Architecture
- **Framework**: FastAPI (Python)
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL (via psycopg2)
- **Task Queue**: Celery with Redis broker
- **Web Scraping**: Playwright with stealth mode, BeautifulSoup for parsing
- **Proxy Management**: Multi-provider system (ScraperAPI primary, Bright Data fallback)
- **API Server**: Uvicorn, runs on port 8000

The backend uses a service-oriented architecture:
- `scraping.py` - Product and search result scraping
- `price_monitor_service.py` - Hepsiburada seller price monitoring
- `trendyol_price_monitor_service.py` - Trendyol-specific price monitoring
- `llm_service.py` - OpenAI integration for product analysis
- `proxy_providers.py` - Abstract proxy provider system with automatic fallback

### Data Layer
- **Primary Database**: PostgreSQL for persistent storage
- **Caching**: Redis for task queue and caching
- **Key Models**: Product, ProductSnapshot, ProductSeller, ProductReview, MonitoredProduct, SellerSnapshot, SearchTask

### Proxy Strategy
The platform uses a hierarchical proxy approach:
1. ScraperAPI (primary, cost-effective with JS rendering)
2. Bright Data (fallback, residential proxies)
3. Direct connection (last resort)

### Deployment Pattern
- Backend serves both API and static frontend assets
- Frontend builds to `frontend/dist` which backend serves at root
- API endpoints prefixed with `/api`
- SPA routing handled by backend catch-all route

## External Dependencies

### Third-Party Services
- **OpenAI API**: GPT-4o-mini for product analysis (requires `OPENAI_API_KEY`)
- **ScraperAPI**: Primary proxy service for web scraping (requires `SCRAPPER_API`)
- **Bright Data**: Fallback residential proxy service (requires `BRIGHT_DATA_ACCOUNT_ID`, `BRIGHT_DATA_ZONE_PASSWORD`)

### Database
- **PostgreSQL**: Primary data store (requires `DATABASE_URL`)
- **Redis**: Task queue and caching (requires `REDIS_URL`)

### Key Python Dependencies
- fastapi, uvicorn - API server
- sqlalchemy, psycopg2-binary - Database ORM
- celery, redis - Background task processing
- playwright, beautifulsoup4 - Web scraping
- openai - LLM integration
- pydantic, pydantic-settings - Configuration management

### Key Frontend Dependencies
- react, react-dom, react-router-dom - Core framework
- axios - HTTP client
- plotly.js, react-plotly.js - Charts
- tailwindcss - Styling