# MarketPulse - Gelistirme Plani (Filtrelenmis)

> Son guncelleme: 2026-02-23
> Baz commit: `34530c58` (main)
> Deployment: Replit Autoscale (stateless, multi-instance)
> Cikarilan/Ertelenen maddeler asagida ayri bolumde listelenmistir.

---

## Cikarilan / Ertelenen Maddeler Ozeti

Asagidaki maddeler autoscale uyumsuzlugu, gereksiz kod karmasikligi veya yuksek risk nedeniyle bu plandan cikarilmis ya da ertelenmistir:

| Madde | Neden | Detay |
|-------|-------|-------|
| **2.4 TLS Dogrulama** | Scraping bozulma riski | Proxy SSL interception nedeniyle `SSL certificate verify failed` hatasi olusabilir. Bilinen hedeflere (HB/TY/YT) istek gonderildiginden risk kabul edilebilir |
| **1.6 Rate Limiting** | Autoscale uyumsuz | `slowapi` in-memory storage kullanir — her instance kendi sayacini tutar. Redis-backed storage gerektirir ama Redis opsiyonel. API key zaten koruma sagliyor |
| **4.2 Sync/Async Gecisi** | Gereksiz karmasiklik | 50+ endpoint'te `async def` → `def` degisikligi. Tek kullanici icin hissedilir fark yok. N+1 fix (4.1) zaten bloklama suresini azaltacak. Ileride kademeli gecis yapilabilir |
| **5.5 scraping.py Refactoring** | Yuksek risk | 1643 satirlik scraping motorunda refactoring. Yanlis yapilirsa tum veri kazima bozulur. Test altyapisi (Faz 3) ve baseline olmadan riskli |
| **2.7 DRY Temizligi** | Kucuk kazanc, scraping riski | `_get_geo_country` birlestirmesi minimal kazanc saglar ama yanlis yapilirsa geotargeting bozulur |

---

## Autoscale Deployment Uyumluluk Notlari

Replit Autoscale deployment'ta su ozellikler gecerlidir:
- **Stateless:** Her instance bagimsiz calisir, in-memory state paylasilmaz
- **Multi-instance:** Birden fazla instance ayni anda calisabilir
- **Cold start:** Instance'lar istek geldiginde baslar, bos kalinca kapanir
- **Build adimi:** `cd frontend && npm install && npm run build` (bir kez calisir)
- **Run komutu:** `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 5000`
- **Production env:** `PRICE_MONITOR_EXECUTOR=local` (Redis gerektirmez)

**Dikkat edilmesi gerekenler:**
- Alembic migration (2.1): Build adiminda calisacak ancak **tek-seferlik garanti yoktur** — ayni anda birden fazla deploy tetiklenebilir. Bu nedenle migration script'i Postgres advisory lock (`pg_advisory_lock`) veya Alembic'in kendi stamp mekanizmasi ile idempotent olmali. Birden fazla instance ayni migration'i ayni anda calistirirsa veri kaybi veya lock hatasi olusabilir
- CORS (2.2): `REPLIT_DOMAINS` fallback'i kesinlikle korunmali — deploy sirasinda config hatasi olursa frontend erisemez hale gelir
- DB Init (1.7): `create_all()` yerine **hafif connectivity check** yapilacak (basit `SELECT 1` sorgusu). Schema yonetimi Alembic'e devredilene kadar `create_all()` korunabilir ama startup'i bloke edecek agir islem olmamalı

---

## Icindekiler

1. [Oncelik Seviyeleri](#oncelik-seviyeleri)
2. [Faz 1: Kritik Guvenlik ve Runtime Bug Fix (P0)](#faz-1-kritik-guvenlik-ve-runtime-bug-fix-p0)
3. [Faz 2: Guvenlik Hardening ve Migration (P1)](#faz-2-guvenlik-hardening-ve-migration-p1)
4. [Faz 3: Test Altyapisi ve Guvenlik Regression (P1)](#faz-3-test-altyapisi-ve-guvenlik-regression-p1)
5. [Faz 4: Performans ve Temel UX (P2)](#faz-4-performans-ve-temel-ux-p2)
6. [Faz 5: Modulerlik ve Refactoring (P2)](#faz-5-modulerlik-ve-refactoring-p2)
7. [Faz 6: Temizlik ve Dokumantasyon (P3)](#faz-6-temizlik-ve-dokumantasyon-p3)
8. [Faz 7: Opsiyonel Ileri Iyilestirmeler (P3)](#faz-7-opsiyonel-ileri-iyilestirmeler-p3)
9. [Uygulama Sirasi ve Efor Tahmini](#uygulama-sirasi-ve-efor-tahmini)

---

## Oncelik Seviyeleri

| Seviye | Aciklama | Zaman Hedefi |
|--------|----------|--------------|
| **P0** | Kritik guvenlik acigi / runtime bug | 1-2 gun |
| **P1** | Guvenlik hardening + migration + test tabani | 1 hafta |
| **P2** | Performans, UX ve modulerlik | 2-4 hafta |
| **P3** | Opsiyonel iyilestirmeler, temizlik | Surekli |

---

## Faz 1: Kritik Guvenlik ve Runtime Bug Fix (P0)

> Hedef: Tum maddeler 1 gunde kapanabilir. Scraping islemleri hicbir maddeden etkilenmez.

---

### 1.1 Path Traversal Guvenlik Acigi

| Bilgi | Deger |
|-------|-------|
| **Dosya** | `backend/app/main.py` satir 136-146 |
| **Durum** | ACIK |
| **Risk** | `../../etc/passwd` benzeri path ile frontend root disina erisim |
| **Efor** | 15 dakika |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Sorunlu kod (satir 140-142):**
```python
file_path = os.path.join(frontend_dist, full_path)
if full_path and os.path.isfile(file_path):
    return FileResponse(file_path)
```

**Yapilacak degisiklik:**
```python
from pathlib import Path

frontend_root = Path(frontend_dist).resolve()
requested = (frontend_root / full_path).resolve()
if full_path and requested.is_file() and str(requested).startswith(str(frontend_root)):
    return FileResponse(str(requested))
```

**Tamamlanma Kriterleri:**
- `curl` ile `/../../../etc/passwd` denemesi 404 donuyor
- `/assets/*` ve SPA route'lari normal calisiyor

---

### 1.2 Frontend API Key Exposure

| Bilgi | Deger |
|-------|-------|
| **Dosya** | `frontend/src/services/api.ts` satir 8-10 |
| **Durum** | ACIK — `VITE_INTERNAL_API_KEY` build-time'da bundle'a gomuluyor |
| **Risk** | DevTools'tan key gorunur, mutating endpoint'lere yetkisiz erisim |
| **Efor** | 30 dakika |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Mevcut kod (api.ts:8-10):**
```typescript
const internalApiKey = import.meta.env.VITE_INTERNAL_API_KEY;
if (internalApiKey) {
  api.defaults.headers.common['X-API-Key'] = internalApiKey;
}
```

**Yapilacak degisiklik:**
1. `VITE_INTERNAL_API_KEY` kullanimini tamamen kaldir
2. Request interceptor: `sessionStorage.getItem('mp_api_key')` → `X-API-Key` header
3. Response interceptor: 401/403/503 durumunda kullanicidan key sor, sessionStorage'a kaydet, istegi tekrarla
4. `.env`'den `VITE_INTERNAL_API_KEY` satirini kaldir

**Yeni kod:**
```typescript
api.interceptors.request.use((config) => {
  const apiKey = sessionStorage.getItem('mp_api_key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if ([401, 403, 503].includes(error.response?.status)) {
      const key = prompt('API Key giriniz:');
      if (key) {
        sessionStorage.setItem('mp_api_key', key);
        error.config.headers['X-API-Key'] = key;
        return api.request(error.config);
      }
    }
    return Promise.reject(error);
  }
);
```

**Tamamlanma Kriterleri:**
- `dist/` iceriginde `VITE_INTERNAL_API_KEY` veya key degeri yok
- Kimliksiz mutating cagrilar 401/403 donuyor
- Key girildikten sonra mutating endpoint'ler calisiyor

---

### 1.3 Runtime Bug: `SellerSnapshot.fetched_at` Yanlis Alan Adi

| Bilgi | Deger |
|-------|-------|
| **Dosya** | `backend/app/api/store_product_routes.py` satir 532 |
| **Durum** | ACIK |
| **Risk** | `AttributeError` → 500 hatasi (model'de `fetched_at` yok, dogru alan `snapshot_date`) |
| **Efor** | 5 dakika |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklik:**
```python
# ONCE:
).order_by(SellerSnapshot.fetched_at.desc()).first()

# SONRA:
).order_by(SellerSnapshot.snapshot_date.desc()).first()
```

**Tamamlanma Kriterleri:**
- Ilgili endpoint 200 donuyor (500 yerine)

---

### 1.4 Kritik Silent Failure: Scrape Job Status

| Bilgi | Deger |
|-------|-------|
| **Dosya** | `backend/app/api/url_scraper_routes.py` satir 351-352 |
| **Durum** | ACIK — bare `except: pass` |
| **Risk** | Job sonsuza kadar `running` kalir |
| **Efor** | 15 dakika |
| **Scraping Etkisi** | OLUMLU — Hatalar loglanir, job durumu dogru guncellenir |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklik:**
```python
        except Exception as e:
            logger.critical(f"URL scrape job finalization failed: {e}", exc_info=True)
            try:
                db.rollback()
                job.status = "failed"
                job.completed_at = datetime.utcnow()
                db.commit()
            except Exception:
                logger.critical("Failed to mark job as failed", exc_info=True)
```

**Tamamlanma Kriterleri:**
- Hata durumunda job `failed` statusune geciyor

---

### 1.5 Kritik Silent Failure: Transcript Job Status

| Bilgi | Deger |
|-------|-------|
| **Dosya** | `backend/app/api/transcript_routes.py` satir 366-367 |
| **Durum** | ACIK — 1.4 ile birebir ayni pattern |
| **Efor** | 15 dakika |
| **Scraping Etkisi** | OLUMLU |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklik:** 1.4 ile ayni pattern.

---

### 1.7 DB Init Thread Race Condition

| Bilgi | Deger |
|-------|-------|
| **Dosya** | `backend/app/main.py` satir 42-43 |
| **Durum** | ACIK |
| **Risk** | DB init ayri thread'de ama route'lar init bitmeden istek alabilir |
| **Efor** | 20 dakika |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET — cold start'ta DB kesinlikle hazir olur |

**Sorunlu kod:**
```python
t = threading.Thread(target=_init_db, daemon=True)
t.start()
# yield — thread tamamlanmadan request gelebilir!
```

**Yapilacak degisiklik:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... api key check, log filter setup ...

    _init_db()  # Senkron — thread yerine dogrudan calistir

    yield
```

**Autoscale notu:** Cold start'ta DB baglanti kontrolu (hafif `SELECT 1`) senkron yapilir — schema olusturma yapilmaz. Bu sayede startup suresi minimal kalir (tipik <100ms). Alembic (Faz 2.1) sonrasi `create_all()` tamamen kaldirilir. DB erisilemedigi durumda uygulama baslamaz ve autoscale baska instance'a yonlendirir.

**Tamamlanma Kriterleri:**
- Uygulama basladiginda DB baglantisi dogrulanmis
- `/health` endpoint'i `db_initialized: true` donuyor
- Startup suresi cold start'ta <1 saniye (DB connectivity check)

---

## Faz 2: Guvenlik Hardening ve Migration (P1)

---

### 2.1 Alembic Migration Entegrasyonu

| Bilgi | Deger |
|-------|-------|
| **Dosyalar** | `backend/app/main.py`, `backend/app/db/database.py`, `backend/requirements.txt`, yeni `alembic/` dizini |
| **Efor** | 1 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET — migration build adiminda calisir |

**Yapilacak degisiklikler:**
1. `alembic` paketini `requirements.txt`'e ekle
2. `alembic init alembic` ile baslat
3. `env.py`'de `from app.db.database import get_engine, Base` + `target_metadata = Base.metadata`
4. Ilk migration'i `autogenerate` ile olustur
5. `main.py`'deki `Base.metadata.create_all()` kaldir
6. Build adimina `cd backend && alembic upgrade head` ekle

**Autoscale notu:** Migration build adiminda calisir ancak concurrent deploy durumunda birden fazla build ayni anda calisabilir. Bu nedenle migration script'i `pg_advisory_lock` ile korunmali veya idempotent olmali. Onerilen yaklasim: Alembic `env.py`'de `SELECT pg_advisory_lock(12345)` → migration → `SELECT pg_advisory_unlock(12345)` pattern'i.

**Tamamlanma Kriterleri:**
- `alembic upgrade head` temiz calisiyor
- `alembic downgrade -1` + `alembic upgrade head` sorunsuz

---

### 2.2 CORS Fallback Sikilastirmasi

| Bilgi | Deger |
|-------|-------|
| **Dosyalar** | `backend/app/main.py` satir 48-53, `backend/app/core/config.py` satir 168-183 |
| **Risk** | Exception durumunda `["*"]`'a fallback |
| **Efor** | 30 dakika |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET — ama `REPLIT_DOMAINS` fallback korunmali |

**Yapilacak degisiklikler:**
1. Exception durumunda `["*"]` yerine `REPLIT_DOMAINS`'ten oku (tamamen bos dondurme — frontend kirilir)
2. `config.py`'de bos origin listesinde `REPLIT_DOMAINS` her zaman dahil edilsin
3. `["*"]` sadece acik `CORS_ALLOWED_ORIGINS=*` ayarlandiginda gecerli olsun

**Duzeltilmis kod:**
```python
# config.py
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
        logger.warning("CORS: No origins configured, only REPLIT_DOMAINS will be allowed")
    return origins if origins else []

# main.py
def _get_cors_origins():
    try:
        from app.core.config import settings
        origins = settings.cors_allowed_origins()
        if not origins:
            logger.warning("CORS: Empty origin list — cross-origin requests will be blocked")
        return origins
    except Exception as e:
        logger.error(f"CORS configuration failed: {e}")
        return []
```

**Autoscale notu:** `REPLIT_DOMAINS` autoscale'de her zaman set edili. Bu fallback sayesinde config hatasi olsa bile frontend erisimi korunur.

**Tamamlanma Kriterleri:**
- `["*"]` sadece explicit ayarlandiginda gecerli
- `REPLIT_DOMAINS` her zaman dahil ediliyor

---

### 2.3 Input Validation ve SSRF Koruma

| Bilgi | Deger |
|-------|-------|
| **Dosyalar** | `backend/app/api/url_scraper_routes.py`, `backend/app/api/routes.py` |
| **Risk** | SSRF, asiri buyuk payload |
| **Efor** | 1.5 saat |
| **Scraping Etkisi** | MINIMUM — Sadece local/private IP'leri engeller |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**
1. `SingleUrlRequest.url` → URL validasyonu + SSRF korumasi
2. Private/local IP araliklari reddet
3. `SearchRequest.keyword` → `Field(..., min_length=1, max_length=200)`
4. `SearchRequest.platform` → `Field(default="hepsiburada", pattern="^(hepsiburada|trendyol)$")`

**Tamamlanma Kriterleri:**
- Local/private hedefler 4xx donuyor
- Hepsiburada/Trendyol URL'leri normal calisiyor

---

### 2.5 Bare `except:` Temizligi

| Bilgi | Deger |
|-------|-------|
| **Dosya** | `backend/app/services/scraping.py` (17 nokta) |
| **Efor** | 1.5 saat |
| **Scraping Etkisi** | OLUMLU — Hata tespiti kolaylasir |
| **Autoscale Uyumlu** | EVET |

**Envanter (scraping.py - 17 nokta):**

| Satirlar | Oncelik | Aciklama |
|----------|---------|----------|
| 1124, 1147, 1161 | Kritik | JSON-LD parsing, float/int donusum |
| 975, 581, 587, 1201, 1207, 1279 | Orta | Playwright, price parsing, genel parsing |
| 1308, 1329, 1346 | Orta | Rich content extraction |
| 1400, 1491, 1498, 1557, 1625 | Dusuk | Seller parsing, search fallback |

**Yapilacak degisiklik:**
- `except:` → `except Exception:` + loglama
- Mevcut davranis korunur (scraping bozulmasin)

**Tamamlanma Kriterleri:**
- `rg "^\s*except:\s*$" backend/` sonucu SIFIR

---

### 2.6 Hata Mesajlarinda Ic Detay Ifsasi

| Bilgi | Deger |
|-------|-------|
| **Dosyalar** | `backend/app/services/llm_service.py`, `backend/app/api/routes.py`, `backend/app/services/price_monitor_service.py` |
| **Risk** | `str(e)` ile internal path, connection string veya API key ifsasi |
| **Efor** | 1 saat |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**
1. Kullaniciya donen hata mesajlarindan `str(e)` kaldir, genel mesaj kullan
2. Detayli hata bilgisini sadece log'a yaz
3. Global exception handler ekle

**Duzeltilmis kod ornegi:**
```python
# llm_service.py
except Exception as e:
    logger.error(f"LLM analysis failed: {type(e).__name__}: {e}")
    return "Analiz sirasinda beklenmeyen bir hata olustu. Lutfen tekrar deneyin."

# main.py — global handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

**Tamamlanma Kriterleri:**
- Hata yanitlari internal path veya stack trace icermiyor

---

## Faz 3: Test Altyapisi ve Guvenlik Regression (P1)

---

### 3.1 Backend Test Temeli

| Bilgi | Deger |
|-------|-------|
| **Dosyalar** | Yeni `backend/tests/` dizini |
| **Efor** | 1 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**
1. `pytest`, `pytest-asyncio`, `httpx` ekle
2. `backend/tests/conftest.py` olustur
3. Smoke testleri: `/health`, `/health/deep`, `/api/products`, `/api/search`

---

### 3.2 Guvenlik Regression Paketi

| Bilgi | Deger |
|-------|-------|
| **Efor** | 0.5-1 gun |

**Yazilacak testler:**
1. Path traversal negatif testi (1.1)
2. Auth negatif testi (1.2)
3. `SellerSnapshot.snapshot_date` query path testi (1.3)
4. SSRF negatif testleri (2.3)

---

### 3.3 Kalite Kapisi

| Bilgi | Deger |
|-------|-------|
| **Efor** | 2 saat |

**Yapilacak degisiklik:**
- `Makefile` veya `scripts/test.sh` ile tek komutla lint + test

---

## Faz 4: Performans ve Temel UX (P2)

---

### 4.1 Backend Performans — N+1 Query

| Bilgi | Deger |
|-------|-------|
| **Dosya** | `backend/app/api/routes.py` |
| **Efor** | 1-1.5 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Dogrulanmis N+1 noktalari:**
- `routes.py` ~satir 423-473: `get_products` — her urun icin ayri `ProductSnapshot` sorgusu
- `routes.py` ~satir 487-493: `get_product` — 3 ayri iliskili sorgu
- `routes.py` ~satir 805-894: `get_monitored_products` — her urun icin 20'ye kadar `SellerSnapshot` sorgusu

**Yapilacak degisiklikler:**
1. `selectinload()` / `joinedload()` ile iliskili verileri tek sorguda cek
2. In-memory filtrelemeyi SQL `WHERE` kosuluna tasi

**Kullanici etkisi:** Sayfa yukleme hizi gozle gorulur sekilde iyilesir.

---

### 4.3 Frontend Performans

| Bilgi | Deger |
|-------|-------|
| **Efor** | 1 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**
1. Plotly.js lazy load + `plotly.js-basic-dist-min` (~4.8MB → ~1MB)
2. Agir hesaplamalari `useMemo` ile cache'le
3. Polling'i task tamamlandiginda durdur

---

### 4.4 Temel UX Iyilestirmeleri

| Bilgi | Deger |
|-------|-------|
| **Efor** | 1-1.5 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**

**a) ErrorBoundary ekle (`App.tsx`)**

**b) Toast kutuphanesi ekle (`sonner` veya `react-hot-toast`)**

**c) 15 native dialog'u degistir:**

| Dosya | Adet | Detay |
|-------|------|-------|
| `PriceMonitor.tsx` | 9 | 7 alert → toast, 1 confirm → modal, 1 alert → toast |
| `CategoryExplorer.tsx` | 4 | 2 alert → toast, 2 confirm → modal |
| `UrlScraper.tsx` | 1 | 1 confirm → modal |
| `VideoTranscripts.tsx` | 1 | 1 confirm → modal |

**Tamamlanma Kriterleri:**
- `rg "alert\(|confirm\(" frontend/src/` sonucu sifir
- ErrorBoundary calisiyor

---

## Faz 5: Modulerlik ve Refactoring (P2)

> On kosul: Faz 3 tamamlanmis olmali (test altyapisi).
> scraping.py refactoring (5.5) ERTELENMISTIR — yuksek risk nedeniyle.

---

### 5.1 `routes.py` Bolme (2161 satir → ~5-6 dosya)

| Bilgi | Deger |
|-------|-------|
| **Efor** | 2-3 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**
1. `price_monitor_routes.py`, `product_routes.py`, `search_routes.py`, `seller_routes.py`, `stats_routes.py`
2. Pydantic modelleri `schemas/` altina tasi
3. Lazy import pattern'lerini koru

---

### 5.2 `api.ts` Bolme (1051 satir)

| Bilgi | Deger |
|-------|-------|
| **Efor** | 1 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**
1. `client.ts`, `types.ts`, feature bazli dosyalar + `index.ts` barrel

---

### 5.3 `PriceMonitor.tsx` Bolme (1010 satir, 31 useState)

| Bilgi | Deger |
|-------|-------|
| **Efor** | 1.5-2 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**
1. `usePriceMonitor.ts` custom hook + alt komponentler
2. 31 useState'i grupla ve reducer/custom hook'a tasi

---

### 5.4 `CategoryExplorer.tsx` Bolme (1584 satir, 42 useState)

| Bilgi | Deger |
|-------|-------|
| **Efor** | 1.5-2 gun |
| **Scraping Etkisi** | YOK |
| **Autoscale Uyumlu** | EVET |

**Yapilacak degisiklikler:**
1. Alt komponentler: `CategoryFilters`, `ResultsTable`, `CategoryStats`, modals
2. 42 useState'i grupla ve reducer/custom hook'a tasi

---

## Faz 6: Temizlik ve Dokumantasyon (P3)

---

### 6.1 Repo Temizligi + `.env.example`

| Bilgi | Deger |
|-------|-------|
| **Efor** | 2 saat |
| **Scraping Etkisi** | YOK |

**Yapilacak degisiklikler:**
1. `attached_assets/` → `.gitignore` + `git rm --cached -r attached_assets/`
2. `hepsiburada_active_products.json` → `.gitignore` + `git rm --cached`
3. `.env.example` olustur (tum env degiskenleri, degerler bos)
4. Deploy ortaminda `DEBUG_SAVE_HTML=false` dogrula

---

### 6.2 Tailwind Token Temizligi (Tema Borcu)

| Bilgi | Deger |
|-------|-------|
| **Efor** | 2-3 saat |
| **Scraping Etkisi** | YOK |

1. `dark-*` isimlerini light tema'ya uygun degistir
2. Hardcoded renkleri Tailwind token'larina cevir

---

### 6.3 `DEPLOY.md` Olustur

| Bilgi | Deger |
|-------|-------|
| **Efor** | 2 saat |

---

### 6.4 `npm audit` ve Paket Hijyeni

| Bilgi | Deger |
|-------|-------|
| **Efor** | 2 saat |

---

### 6.5 Isimlendirme Tutarliligi

| Bilgi | Deger |
|-------|-------|
| **Efor** | 1 saat |
| **Scraping Etkisi** | MINIMUM |

1. Tek isim: `SCRAPER_API_KEY` (eski `SCRAPPER_API` / `SCRAPPPER_API` kaldir)
2. `.env` ve `.env.example` guncelle

---

## Faz 7: Opsiyonel Ileri Iyilestirmeler (P3)

Bu maddeler opsiyoneldir ve gerektiginde uygulanabilir:

| Madde | Aciklama | Not |
|-------|----------|-----|
| Bearer Auth gecisi | sessionStorage → JWT/session auth | |
| Tam CI pipeline | GitHub Actions + branch protection | |
| Derin a11y | `aria-label`, keyboard navigation, ESC modal | |
| Async SQLAlchemy gecisi | Lazy engine'den async engine'e | Kademeli gecis yapilabilir |
| Sync/Async endpoint gecisi | `async def` → `def` (event loop bloklama) | Kademeli gecis yapilabilir — ayni app'te her iki tip calisir |
| `except Exception:` log standardizasyonu | `main.py` health check'lerdeki pattern'ler | |
| Rate Limiting | `slowapi` + Redis-backed storage | Autoscale uyumlu olmasi icin Redis gerekir |
| scraping.py Refactoring | 1643 satir → modullere bolme | Test altyapisi + baseline zorunlu |
| DRY Temizligi | `_get_geo_country` birlestirme | Scraping testi ile birlikte |

---

## Uygulama Sirasi ve Efor Tahmini

### Onerilen Siralama

```
Hafta 1:   Faz 1 (P0 — 1 gun) + Faz 2 (P1 — 3-4 gun)
Hafta 2:   Faz 3 (test altyapisi — 2-3 gun) + Faz 4 baslangic
Hafta 3-4: Faz 4 tamamlama + Faz 5 (kucuk parcalar halinde refactor)
Hafta 5:   Regression test + fix (refactoring sonrasi)
Hafta 6:   Faz 6 (temizlik + tema borcu) + Faz 7'den secilen maddeler
```

### Efor Tahmini (Filtrelenmis Plan)

| Faz | Aciklama | Tahmini Efor |
|-----|----------|--------------|
| 1 | Kritik guvenlik + runtime bug fix + DB init | ~1 gun |
| 2 | Migration + CORS + validation + bare except + hata mesajlari | ~4-5 gun |
| 3 | Test altyapisi + regression + kalite kapisi | ~2-3 gun |
| 4 | N+1 + frontend perf + UX (sync/async HARIC) | ~3-4 gun |
| 5 | Modulerlik / refactoring (4 dosya, scraping.py HARIC) | ~6-8 gun |
| 6 | Temizlik + tema borcu + dokumantasyon | ~2-3 gun |
| **Alt Toplam** | | **~18-24 is gunu** |
| **Regression/test buffer (+25%)** | Refactoring sonrasi regression fix + ek test | **~5-6 gun** |
| **Toplam (Faz 1-6)** | | **~23-30 is gunu (5-6 hafta)** |

> Efor tahmini tek muhendis icin hesaplanmistir. Faz 5 (refactoring) sonrasi regression riski yuksektir — test altyapisi (Faz 3) tamamlanmadan baslanmamalidir.
> Ertelenen maddeler (rate limiting, sync/async, scraping.py refactor, DRY, TLS) dahil edildiginde ~6-8 gun ek efor beklenir.

---

## Kilit Kararlar

1. Frontend bundle'inda paylasilan sabit mutating secret olmayacak (1.2)
2. `except: pass` kalibi hicbir dosyada kalmayacak (2.5)
3. Buyuk refactorlar (Faz 5) test altyapisi (Faz 3) olmadan baslamayacak
4. Replit'teki lazy initialization pattern'leri korunacak (engine, Celery, import)
5. TLS dogrulama cikarildi — scraping proxy uyumlulugu korunuyor
6. Rate limiting ertelendi — autoscale'de in-memory storage uyumsuz, API key yeterli koruma
7. Sync/async gecisi ertelendi — kademeli gecis icin Faz 7'ye tasindi
8. scraping.py refactoring ertelendi — test altyapisi + baseline olmadan riskli
9. DRY temizligi ertelendi — kucuk kazanc, scraping bozulma riski
10. CORS fallback'te `REPLIT_DOMAINS` kesinlikle korunacak
11. Alembic migration build adiminda calisacak (autoscale uyumlu)
12. Her faz olculebilir DoD ile kapanacak

---

*Guncel kod tabani denetimi ve grep/LSP dogrulamasi ile olusturulmustur.*
*Autoscale deployment uyumlulugu icin filtrelenmistir.*
*Son guncelleme: 2026-02-23*
