# Faz 2: Guvenlik Hardening ve Migration — Implementation Plan

> **Durum: TAMAMLANDI — Tüm görevler uygulanmis ve test edilmistir (commit f2a74d1).**

> **Not: Faz 5 sonrasi routes.py barrel modüle dönüstü. Bu plandaki routes.py satir referanslari artik gecersizdir.**

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** CORS wildcard fallback'i kapat, hata mesaji sizintilarini duzelt, SSRF korumasiekle, bare except'leri temizle, Alembic migration altyapisini kur.

**Architecture:** Backend-only degisiklikler. Scraping motoru davranisi korunur (sadece loglama eklenir). Tum degisiklikler Replit Autoscale uyumlu.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL

**Siralama:** 2.2 → 2.6 → 2.3 → 2.5 → 2.1 (basitten karmasiga)

---

## Task 1: CORS Fallback Sikilastirmasi (2.2)

**Files:**
- Modify: `backend/app/core/config.py:168-183`
- Modify: `backend/app/main.py:47-52`

**Step 1: Read current CORS code**

Read `backend/app/core/config.py` lines 168-183 and `backend/app/main.py` lines 47-52.

**Step 2: Fix config.py — remove wildcard fallback**

In `backend/app/core/config.py`, replace the `cors_allowed_origins` method:

```python
def cors_allowed_origins(self) -> List[str]:
    raw = (self.CORS_ALLOWED_ORIGINS or "").strip()
    if raw == "*":
        return ["*"]
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    replit_domains = os.getenv("REPLIT_DOMAINS", "")
    if replit_domains:
        for domain in replit_domains.split(","):
            d = domain.strip()
            if d:
                https_origin = f"https://{d}"
                if https_origin not in origins:
                    origins.append(https_origin)
    if not origins:
        logger.warning("CORS: No origins configured and no REPLIT_DOMAINS found")
    return origins
```

Key change: `if not origins: return ["*"]` REMOVED — returns empty list instead.

**Step 3: Fix main.py — exception handler reads REPLIT_DOMAINS as last defense**

In `backend/app/main.py`, replace the `_get_cors_origins` function:

```python
def _get_cors_origins():
    try:
        from app.core.config import settings
        origins = settings.cors_allowed_origins()
        if not origins:
            logger.warning("CORS: Empty origin list — cross-origin requests will be blocked")
        return origins
    except Exception as e:
        logger.error(f"CORS configuration failed: {e}")
        # Last defense: read REPLIT_DOMAINS directly
        replit_domains = os.getenv("REPLIT_DOMAINS", "")
        if replit_domains:
            fallback = []
            for domain in replit_domains.split(","):
                d = domain.strip()
                if d:
                    fallback.append(f"https://{d}")
            if fallback:
                logger.warning(f"CORS: Using REPLIT_DOMAINS fallback: {fallback}")
                return fallback
        return []
```

Key change: Exception handler no longer returns `["*"]` — reads REPLIT_DOMAINS as son savunma hatti.

**Step 4: Verify**

Run: `grep -n '"\*"' backend/app/main.py | grep -i cors` — should return ZERO wildcard in CORS handler
Run: `grep -n 'return \["\*"\]' backend/app/core/config.py` — should return ONLY the explicit `raw == "*"` case (line ~170)

---

## Task 2: Hata Mesaji Sizintisi + Global Handler (2.6)

**Files:**
- Modify: `backend/app/services/llm_service.py:47`
- Modify: `backend/app/api/store_product_routes.py:568`
- Modify: `backend/app/api/routes.py:983`
- Modify: `backend/app/services/price_monitor_service.py:539`
- Modify: `backend/app/main.py` (global exception handler ekle)

### str(e) Envanteri

**Kullaniciya donen (DUZELTILMELI):**

| Dosya | Satir | Sorun |
|-------|-------|-------|
| `llm_service.py` | 47 | `return f"...hata olustu: {str(e)}"` — LLM exception details leak |
| `store_product_routes.py` | 568 | `HTTPException(detail=f"Invalid Excel file: {str(e)}")` — openpyxl internals leak |
| `routes.py` | 983 | `errors.append({..."error": str(e)})` — DB constraint names leak |
| `price_monitor_service.py` | 539 | `result['error'] = str(e)` — scraping internals leak |

**DB'ye kaydedilen (KABUL EDILEBILIR — endpoint'lerde goruntulenmediysene dokunma):**

| Dosya | Satir | Durum |
|-------|-------|-------|
| `url_scraper_routes.py` | 338 | `job.error_message = str(e)` — DB only |
| `transcript_routes.py` | 353 | `job.error_message = str(e)` — DB only |
| `routes.py` | 504 | `task.error_message = str(e)` — DB only |
| `tasks.py` | 73 | `task.error_message = str(e)` — DB only |
| `url_scraper_service.py` | 614 | `error_message = str(e)` — DB only |
| `transcript_service.py` | 140, 253 | `error_msg = str(e)` — DB only |

**Step 1: Read each file at the specified lines**

Read all 4 user-facing files to understand the full context around each `str(e)`.

**Step 2: Fix llm_service.py:47**

```python
# BEFORE:
            return f"Analiz sırasında hata oluştu: {str(e)}"

# AFTER:
            logger.error(f"LLM analysis failed: {type(e).__name__}: {e}")
            return "Analiz sirasinda beklenmeyen bir hata olustu. Lutfen tekrar deneyin."
```

**Step 3: Fix store_product_routes.py:568**

```python
# BEFORE:
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {str(e)}")

# AFTER:
        logger.error(f"Excel import failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Gecersiz Excel dosyasi. Lutfen dosya formatini kontrol edin.")
```

**Step 4: Fix routes.py:983**

```python
# BEFORE:
            errors.append({"sku": item.sku or item.productUrl, "error": str(e)})

# AFTER:
            logger.error(f"Bulk import item failed (sku={item.sku or item.productUrl}): {type(e).__name__}: {e}")
            errors.append({"sku": item.sku or item.productUrl, "error": "Urun eklenirken hata olustu"})
```

**Step 5: Fix price_monitor_service.py:539**

```python
# BEFORE:
            result['error'] = str(e)

# AFTER:
            logger.error(f"Price monitor check failed for {product_id}: {type(e).__name__}: {e}")
            result['error'] = "Fiyat kontrolu sirasinda hata olustu"
```

**Step 6: Add global exception handler to main.py**

Add after the `app = FastAPI(...)` block, before CORS middleware:

```python
from starlette.requests import Request
from starlette.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

Note: `Request` and `JSONResponse` may already be imported — check first.

**Step 7: Verify**

Run: `grep -n "str(e)" backend/app/services/llm_service.py backend/app/api/store_product_routes.py backend/app/api/routes.py backend/app/services/price_monitor_service.py`
Expected: ZERO results in these 4 files

Run: `grep -n "global_exception_handler" backend/app/main.py`
Expected: Handler defined

---

## Task 3: Input Validation + SSRF Koruma (2.3)

**Files:**
- Modify: `backend/app/api/url_scraper_routes.py` (SingleUrlRequest model)
- Modify: `backend/app/api/routes.py` (SearchRequest model)
- Create: `backend/app/core/url_validator.py` (SSRF validation utility)

**Step 1: Create URL validation utility**

Create `backend/app/core/url_validator.py`:

```python
import socket
import ipaddress
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}

def validate_url_safe(url: str) -> tuple[bool, str]:
    """
    Validate that a URL is safe to scrape (not targeting private/local IPs).
    Returns (is_safe, error_message).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Gecersiz URL formati"

    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, f"Sadece HTTP/HTTPS desteklenir"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL'de hostname bulunamadi"

    try:
        resolved_ip = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(resolved_ip)
    except (socket.gaierror, ValueError):
        return False, "Hostname cozumlenemedi"

    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        logger.warning(f"SSRF attempt blocked: {url} -> {resolved_ip}")
        return False, "Private/local adresler desteklenmez"

    return True, ""
```

**Step 2: Read url_scraper_routes.py to find SingleUrlRequest model**

Find the Pydantic model and the endpoint that uses it.

**Step 3: Add SSRF check to URL scraper endpoint**

In the endpoint that accepts SingleUrlRequest, add validation before processing:

```python
from app.core.url_validator import validate_url_safe

# Inside the endpoint handler, before creating the job:
is_safe, error_msg = validate_url_safe(request.url)
if not is_safe:
    raise HTTPException(status_code=400, detail=error_msg)
```

**Step 4: Read routes.py to find SearchRequest model**

Find the Pydantic model definition.

**Step 5: Add field validation to SearchRequest**

```python
# Find the SearchRequest model and update fields:
class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    platform: str = Field(default="hepsiburada", pattern=r"^(hepsiburada|trendyol)$")
    # ... rest of fields unchanged
```

**Step 6: Verify**

Run: `grep -n "validate_url_safe" backend/app/api/url_scraper_routes.py` — should show import + usage
Run: `grep -n "min_length\|max_length\|pattern" backend/app/api/routes.py` — should show field constraints

---

## Task 4: Bare `except:` Temizligi — scraping.py (2.5)

**Files:**
- Modify: `backend/app/services/scraping.py` (17 nokta)

**Step 1: Find all bare except locations**

Run: `grep -n "^[[:space:]]*except:[[:space:]]*$" backend/app/services/scraping.py`

**Step 2: Read context around each bare except**

For each location, read 5 lines before and 5 lines after to understand the context.

**Step 3: Replace all 17 bare excepts**

Replace each `except:` with `except Exception as e:` + appropriate logging.

**Log severity guide:**
- **Parse hatalari (JSON-LD, float/int donusum):** `logger.debug` — bunlar normal isleyisin parcasi, her urun icin olusabilir
  - Lines: 1124, 1147, 1161, 1201, 1207, 1279, 1308, 1329, 1346, 1400, 1491, 1498, 1557, 1625
- **Network/Playwright hatalari:** `logger.warning` — bunlar beklenmedik, dikkat gerektirir
  - Lines: 975, 581, 587

**Pattern:**
```python
# Parse hatalari (debug):
# BEFORE:
except:
    pass  # or fallback value

# AFTER:
except Exception as e:
    logger.debug(f"[context description]: {e}")
    pass  # or same fallback value — PRESERVE EXISTING BEHAVIOR

# Network/Playwright hatalari (warning):
# BEFORE:
except:
    # some fallback

# AFTER:
except Exception as e:
    logger.warning(f"[context description]: {e}")
    # same fallback — PRESERVE EXISTING BEHAVIOR
```

**CRITICAL:** Mevcut davranis (pass, fallback deger, continue, vb.) KESINLIKLE korunmali. Sadece except turunu ve loglamayi ekliyoruz.

**Step 4: Verify**

Run: `grep -n "^[[:space:]]*except:[[:space:]]*$" backend/app/services/scraping.py`
Expected: ZERO results

Run: `grep -c "except Exception" backend/app/services/scraping.py`
Expected: 17 or more (mevcut olanlar + yeni eklenenler)

---

## Task 5: Alembic Migration Entegrasyonu (2.1)

**Files:**
- Modify: `backend/requirements.txt` (alembic ekle)
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (initial migration)
- Modify: `backend/app/main.py` (create_all kaldir)

**Step 1: Add alembic to requirements.txt**

```
alembic>=1.13.0
```

**Step 2: Initialize alembic**

```bash
cd /Users/projectx/Desktop/marketpulse/backend && pip install alembic && alembic init alembic
```

**Step 3: Configure alembic.ini**

Edit `backend/alembic.ini`:
- Set `sqlalchemy.url` to empty (will be overridden by env.py)
- Or comment it out

**Step 4: Configure env.py with advisory lock**

Replace `backend/alembic/env.py` with:

```python
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import get_engine, Base
from app.db import models  # noqa: F401 — ensure all models are imported

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()

    with connectable.connect() as connection:
        # Advisory lock for concurrent deploy protection
        connection.execute(text("SELECT pg_advisory_lock(2026022301)"))
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(2026022301)"))
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 5: Generate initial migration**

```bash
cd /Users/projectx/Desktop/marketpulse/backend && alembic revision --autogenerate -m "initial schema from existing tables"
```

**CRITICAL:** Autogenerate ciktisini gozden gecir! Bazen gereksiz DROP TABLE uretebilir. Migration dosyasinda:
- `upgrade()`: Sadece CREATE TABLE / CREATE INDEX olmali
- `downgrade()`: Sadece DROP TABLE / DROP INDEX olmali
- Eger mevcut tablolarla ilgili DROP var ise, o satirlari kaldir

**Step 6: Test migration**

```bash
cd /Users/projectx/Desktop/marketpulse/backend && alembic upgrade head
```
Expected: No errors (tables already exist, should be no-op or idempotent)

```bash
cd /Users/projectx/Desktop/marketpulse/backend && alembic downgrade -1 && alembic upgrade head
```
Expected: Clean downgrade and upgrade cycle

**Step 7: Remove create_all from main.py**

In `backend/app/main.py`, modify the `_init_db` function:

```python
def _init_db():
    global _db_initialized
    try:
        from app.db.database import get_engine
        eng = get_engine()
        # Verify DB connectivity (schema managed by Alembic)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        _db_initialized = True
        logger.info("Database connection verified successfully")
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
```

Add `from sqlalchemy import text` to the imports if not present.

**Step 8: Verify**

Run: `grep -n "create_all" backend/app/main.py` — ZERO results
Run: `alembic current` (from backend dir) — shows current revision
Run: `alembic heads` — shows head revision

---

## Final Verification Checklist

After all tasks complete:

```bash
# 1. CORS: No wildcard fallback (except explicit *)
grep -n 'return \["\*"\]' backend/app/core/config.py
# Expected: Only 1 result (the raw == "*" case)

# 2. Error messages: No str(e) in user-facing code
grep -n "str(e)" backend/app/services/llm_service.py backend/app/api/store_product_routes.py backend/app/api/routes.py backend/app/services/price_monitor_service.py
# Expected: ZERO results

# 3. Global exception handler exists
grep -n "global_exception_handler" backend/app/main.py
# Expected: 1 result

# 4. SSRF validator exists
ls backend/app/core/url_validator.py
# Expected: File exists

# 5. No bare except in scraping.py
grep -n "^[[:space:]]*except:[[:space:]]*$" backend/app/services/scraping.py
# Expected: ZERO results

# 6. No bare except in entire backend (excluding scraping edge cases)
grep -rn "^[[:space:]]*except:[[:space:]]*$" backend/
# Expected: ZERO results

# 7. Alembic configured
ls backend/alembic/versions/*.py
# Expected: Initial migration file

# 8. create_all removed
grep -n "create_all" backend/app/main.py
# Expected: ZERO results

# 9. Python syntax valid
python3 -c "
import ast
files = [
    'backend/app/main.py',
    'backend/app/core/config.py',
    'backend/app/services/llm_service.py',
    'backend/app/api/routes.py',
    'backend/app/api/store_product_routes.py',
    'backend/app/services/price_monitor_service.py',
    'backend/app/services/scraping.py',
    'backend/app/core/url_validator.py',
]
for f in files:
    ast.parse(open(f).read())
    print(f'{f}: OK')
"
```
