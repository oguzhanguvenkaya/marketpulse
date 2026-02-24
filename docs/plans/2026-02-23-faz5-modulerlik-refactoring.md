# Faz 5: Modulerlik ve Refactoring — Detayli Uygulama Plani

> **Durum: TAMAMLANDI (commit 6ef31ab)**

> Tarih: 2026-02-23
> On kosul: Faz 3 (test altyapisi) tamamlanmis
> Kapsam: 5.1 routes.py bolme + 5.2 api.ts bolme (5.3, 5.4 zaten tamamlandi)

---

## 5.1 Backend: `routes.py` Bolme (2163 satir → 7 dosya, routes.py artik 27 satirlik barrel modül)

### Hedef Yapi

```
backend/app/api/
├── routes.py              ← Sadece barrel import (geriye uyumluluk)
├── _shared.py             ← Ortak helper fonksiyonlar + schemas
├── search_routes.py       ← /search, /tasks, /search/{id}/sponsored-*
├── product_routes.py      ← /products, /products/{id}, /products/{id}/snapshots, /analyze
├── stats_routes.py        ← /stats, /scraping/status, /stats/trends
├── price_monitor_routes.py← /price-monitor/* (14 endpoint)
└── seller_routes.py       ← /sellers, /sellers/{id}/products, /sellers/{id}/export
```

### Dosya Icerikleri

#### `_shared.py` (Ortak kod — satir 1-297)
- Imports: fastapi, sqlalchemy, pydantic, models, config, security
- Helper fonksiyonlar: `_to_float`, `_calculate_price_alerts`, `_parse_review_date`, `_is_valid_http_url`, `_build_product_search_url`, `_resolve_product_url`, `_require_scraper_api_or_503`, `_is_queue_reachable`, `_require_queue_or_503`, `_is_retryable_db_operational_error`, `_run_read_query_with_retry`
- Lazy service getters: `_get_scraping_service`, `_get_proxy_status`, `_get_llm_service`, `_get_price_monitor_service`, `_get_trendyol_price_monitor_service`
- Schemas: SearchRequest, AnalysisRequest, SearchTaskResponse, CouponResponse, CampaignResponse, SellerResponse, ReviewResponse, ProductResponse, ProductDetailResponse, SnapshotResponse
- Schemas: MonitoredProductInput, BulkProductsRequest, MonitoredProductResponse, SellerSnapshotResponse, ProductWithSellersResponse, FetchTaskResponse, `extract_sku_from_url`

#### `search_routes.py` (satir 298-614)
- Router: `router = APIRouter(prefix="/api", dependencies=[Depends(require_mutating_api_key)])`
- `run_scraping_background()` background function
- `POST /search` → create_search_task
- `GET /search/{task_id}` → get_search_task
- `GET /tasks` → list_tasks
- `GET /search/{task_id}/sponsored-brands` → get_sponsored_brands
- `GET /search/{task_id}/sponsored-products` → get_sponsored_products

#### `product_routes.py` (satir 616-793)
- `GET /products` → list_products
- `GET /products/{product_id}` → get_product
- `GET /products/{product_id}/snapshots` → get_product_snapshots
- `POST /analyze` → analyze_products

#### `stats_routes.py` (satir 795-817)
- `GET /stats` → get_stats
- `GET /scraping/status` → get_scraping_status
- (trends endpoint zaten varsa dahil et)

#### `price_monitor_routes.py` (satir 819-1716)
- `POST /price-monitor/products` → add_monitored_products
- `GET /price-monitor/products` → get_monitored_products
- `GET /price-monitor/export` → export_price_monitor_data
- `GET /price-monitor/brands` → get_monitored_product_brands
- `GET /price-monitor/products/{product_id}` → get_monitored_product_detail
- `DELETE /price-monitor/products/{product_id}` → delete_monitored_product
- `DELETE /price-monitor/products/bulk/all` → delete_all_monitored_products
- `DELETE /price-monitor/products/bulk/inactive` → delete_inactive_monitored_products
- `run_fetch_task()` background function
- `POST /price-monitor/fetch` → start_fetch_task
- `POST /price-monitor/fetch/{task_id}/stop` → stop_fetch_task
- `GET /price-monitor/fetch/{task_id}` → get_fetch_task_status
- `GET /price-monitor/last-inactive` → get_last_inactive_skus
- `POST /price-monitor/fetch-single/{product_id}` → fetch_single_product

#### `seller_routes.py` (satir 1718-2163)
- Helper: `_compute_seller_pricing`, `_build_seller_products`
- `GET /sellers` → get_sellers
- `GET /sellers/{merchant_id}/products` → get_seller_products
- `GET /sellers/{merchant_id}/export` → export_seller_products

### `main.py` Guncelleme
- Mevcut `from app.api.routes import router` satirini koru (geriye uyumluluk)
- Yeni router'lari kaydet:
  - search_routes, product_routes, stats_routes, price_monitor_routes, seller_routes

### `routes.py` → Barrel (geriye uyumluluk)
- Sadece router import ve re-export (test'ler bozulmasin)

---

## 5.2 Frontend: `api.ts` Bolme (1120 satir → 7 dosya, api.ts artik 12 satirlik barrel modül)

### Hedef Yapi

```
frontend/src/services/
├── api.ts                 ← Barrel: re-export everything
├── client.ts              ← Axios instance + interceptors + cache utils
├── types.ts               ← Tum TypeScript interface'leri
├── searchApi.ts           ← Search/task fonksiyonlari
├── productApi.ts          ← Product CRUD + analyze
├── priceMonitorApi.ts     ← Price monitor fonksiyonlari
├── sellerApi.ts           ← Seller fonksiyonlari
├── scrapeApi.ts           ← URL scraper fonksiyonlari
├── transcriptApi.ts       ← Transcript fonksiyonlari
├── storeProductApi.ts     ← Store product fonksiyonlari
└── categoryApi.ts         ← Category explorer fonksiyonlari
```

### Geriye Uyumluluk
- `api.ts` tum export'lari re-export eder
- Hicbir import degisikligi gerekmez (mevcut kodlar `from '../services/api'` kullanmaya devam eder)

---

## Dogrulama

1. Backend: `pytest` tum testler gecmeli
2. Frontend: `npm run build` basarili olmali
3. Mevcut import'lar bozulmamali (barrel pattern)
4. Tum endpoint'ler ayni URL'lerde calismali
