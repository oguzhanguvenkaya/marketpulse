# MarketPulse — Deployment Guide (Replit Autoscale)

## Prerequisites

- Replit account with Autoscale deployment capability
- PostgreSQL database (e.g., Neon, Supabase, or Replit DB)
- ScraperAPI key for scraping features

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### Required

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string with `?sslmode=require` |
| `INTERNAL_API_KEY` | Internal API authentication key |

### Scraping / Proxy

| Variable | Description |
|---|---|
| `SCRAPER_API_KEY` | ScraperAPI key (canonical name) |

### Optional

| Variable | Default | Description |
|---|---|---|
| `PRICE_MONITOR_EXECUTOR` | `celery` | Use `local` for single-process mode (recommended for Replit) |
| `DEBUG_SAVE_HTML` | `false` | Save raw HTML responses to disk for debugging |
| `CORS_ALLOWED_ORIGINS` | `localhost:5173` | Comma-separated origins. `REPLIT_DOMAINS` auto-detected |
| `OPENAI_API_KEY` | — | For AI-powered transcript summaries |
| `REDIS_URL` | — | Redis connection string (gerekli sadece celery executor kullanildiginda) |
| `PROXY_PROVIDER` | `auto` | auto/scraperapi/direct (varsayilan: auto) |

## Build

```bash
cd frontend && npm install && npm run build
```

This compiles TypeScript and produces a production bundle in `frontend/dist/`.

## Run

```bash
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 5000
```

The backend serves both the API and the frontend static files from `frontend/dist/`.

## Replit Configuration

### Autoscale Settings

- **Run command:** `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 5000`
- **Build command:** `cd frontend && npm install && npm run build`
- **Port:** 5000

### CORS

CORS origins are auto-detected from the `REPLIT_DOMAINS` environment variable, which Replit sets automatically. No manual CORS configuration is needed.

### Recommended Config

```
PRICE_MONITOR_EXECUTOR=local
DEBUG_SAVE_HTML=false
```

- `local` executor runs price monitoring in-process (no Redis/Celery needed)
- `DEBUG_SAVE_HTML=false` prevents disk fill-up in production

## Notes

- The `SCRAPPER_API` env var name is deprecated but still accepted with a warning log. Use `SCRAPER_API_KEY` instead.
- Database pool settings (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, etc.) can be tuned via env vars. See `.env.example` for defaults.
- The frontend uses Tailwind CSS v4 with a semantic token system. All theme colors auto-switch between light and dark modes.
