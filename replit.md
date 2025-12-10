# Pazaryeri Veri Analiz Platformu

## Overview
A Marketplace Data Analysis Platform that helps marketplace sellers and marketing agencies make data-driven decisions. The platform scrapes product data from Turkish marketplaces (starting with Hepsiburada), analyzes trends, and provides AI-powered insights.

## Current State
- **Status**: MVP Phase 1 Complete
- **Backend**: FastAPI with PostgreSQL, BackgroundTasks for async scraping
- **Frontend**: React + Vite + TailwindCSS v4
- **Features**: Product search, data scraping, price/rating charts, AI analysis
- **Note**: Using FastAPI BackgroundTasks instead of Celery/Redis for simplicity in MVP

## Project Structure
```
.
├── backend/
│   ├── app/
│   │   ├── api/routes.py         # API endpoints
│   │   ├── core/config.py        # Configuration
│   │   ├── db/
│   │   │   ├── database.py       # SQLAlchemy setup
│   │   │   └── models.py         # Product, Snapshot, Task models
│   │   ├── services/
│   │   │   ├── scraping.py       # Playwright + Bright Data scraping
│   │   │   └── llm_service.py    # OpenAI integration
│   │   ├── tasks.py              # Celery async tasks
│   │   └── main.py               # FastAPI app entry
│   ├── run.py                    # Backend runner
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/Layout.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx     # Main dashboard with search
│   │   │   ├── Products.tsx      # Product list
│   │   │   └── ProductDetail.tsx # Product details with charts
│   │   └── services/api.ts       # API client
│   ├── package.json
│   └── vite.config.ts
└── replit.md
```

## Running the Project
- **Frontend**: Runs on port 5000 (webview)
- **Backend**: Runs on port 8000 (localhost)

## Environment Variables Required
- `DATABASE_URL` - PostgreSQL connection (auto-configured by Replit)
- `OPENAI_API_KEY` - For AI analysis features
- `BRIGHT_API_KEY` - For Bright Data proxy (scraping)
- `REDIS_URL` - For Celery task queue (optional)

## Tech Stack
- **Frontend**: React 18, TypeScript, TailwindCSS v4, Plotly.js, React Router
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, BackgroundTasks
- **Scraping**: Playwright, BeautifulSoup4, Bright Data proxy
- **Database**: PostgreSQL (Replit built-in)
- **AI**: OpenAI GPT-4o-mini

## API Endpoints
- `POST /api/search` - Start a new search task
- `GET /api/search/{id}` - Get task status
- `GET /api/tasks` - List recent tasks
- `GET /api/products` - List products
- `GET /api/products/{id}` - Get product details
- `GET /api/products/{id}/snapshots` - Get price/rating history
- `POST /api/analyze` - AI analysis of products
- `GET /api/stats` - Dashboard statistics

## User Preferences
- Turkish language UI
- Focus on Hepsiburada marketplace initially

## Recent Changes
- December 10, 2025: Initial MVP implementation with scraping, dashboard, and AI analysis
