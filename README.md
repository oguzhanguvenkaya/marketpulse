# marketing_agent

## Runtime Profile (Local)

### 1) Redis
Celery broker/backend uses `REDIS_URL` (default: `redis://localhost:6379/0`).

### 2) Backend API
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3) Celery Worker (Price Monitor + Search Jobs)
```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

### 4) Frontend (optional for manual QA)
```bash
cd frontend
npm run dev
```

## Key Environment Variables

### Required
- `DATABASE_URL`
- `INTERNAL_API_KEY`
- `SCRAPER_API_KEY` (fallbacks: `SCRAPPER_API`, `SCRAPPPER_API`)

### Price Monitor Execution
- `PRICE_MONITOR_EXECUTOR=celery|local` (default: `celery`)
- `PRICE_MONITOR_MAX_CONCURRENT_REQUESTS=17`

### DB Pool Resiliency (Neon/Postgres)
- `DB_POOL_SIZE=5`
- `DB_MAX_OVERFLOW=10`
- `DB_POOL_TIMEOUT_SECONDS=30`
- `DB_POOL_RECYCLE_SECONDS=180`

### Frontend Read Cache
- `VITE_QUERY_CACHE_TTL_MS=45000`
- `VITE_DISABLE_STRICT_MODE=true` (local dev only)

## Verification Commands

### Runtime preflight (DB + queue)
```bash
cd backend
python3 scripts/runtime_preflight.py --timeout 2
```

### Fetch E2E smoke
```bash
cd backend
python3 scripts/e2e_fetch_smoke.py --base-url http://127.0.0.1:8000 --platform hepsiburada --fetch-type active
```

### Frontend request frequency QA (Playwright/Firefox)
```bash
cd frontend
python3 scripts/request_frequency_qa.py --frontend-url http://127.0.0.1:5173 --api-base-url http://127.0.0.1:8000
```

## Troubleshooting

- Fetch starts but does not progress:
  - Confirm Redis and Celery worker are running.
  - Check `/health` response (`database_reachable`, `queue_reachable`, `scraper_api_configured`, `price_monitor_executor`).
- `POST /api/price-monitor/fetch` returns `503`:
  - Queue guard is rejecting enqueue because Redis is unreachable.
  - Verify `REDIS_URL`, Redis process, and worker startup.
- Frequent DB connection drops:
  - Keep `DB_POOL_RECYCLE_SECONDS` low (recommended `180`).
  - Verify Neon connection URL and SSL params.
- UI repeatedly re-fetches list endpoints:
  - Run `frontend/scripts/request_frequency_qa.py` and inspect failed endpoint counters.
  - Check browser console for aborted request errors (expected during quick filter/search changes).
