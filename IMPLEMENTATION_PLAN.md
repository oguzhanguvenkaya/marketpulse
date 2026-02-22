# MarketPulse - Implementation Plan (Geliştirme Planı)

**Oluşturulma Tarihi:** 2026-02-22
**Kaynak:** 3 bağımsız code review raporu (Claude Opus, Codex, Gemini)
**Durum:** Planlandı - Onay bekliyor

---

## Öncelik Seviyeleri

| Seviye | Açıklama | Zaman Hedefi |
|--------|----------|--------------|
| **P0** | Güvenlik açığı / Runtime bug - Hemen düzeltilmeli | 1-2 gün |
| **P1** | Önemli teknik borç - Kısa vadede düzeltilmeli | 1 hafta |
| **P2** | İyileştirme - Orta vadede yapılmalı | 2-4 hafta |
| **P3** | Nice-to-have - Zaman buldukça yapılır | Süresiz |

---

## FAZA 1: Kritik Güvenlik ve Bug Fix'ler (P0)

### 1.1 Path Traversal Güvenlik Açığı
**Dosya:** `backend/app/main.py:91-97`
**Kaynak:** Codex Review
**Risk:** Saldırgan `../../etc/passwd` gibi path ile sunucudan dosya okuyabilir
**Efor:** 15 dakika

**Görevler:**
- [ ] `serve_spa` fonksiyonunda `pathlib.Path.resolve()` ile canonical path doğrulaması ekle
- [ ] `frontend_root` dışına çıkan path'leri reddet
- [ ] Test: `curl` ile `/../../../etc/passwd` denemesi yaparak doğrula

**Önce:**
```python
file_path = os.path.join(frontend_dist, full_path)
if full_path and os.path.isfile(file_path):
    return FileResponse(file_path)
```

**Sonra:**
```python
from pathlib import Path
frontend_root = Path(frontend_dist).resolve()
requested = (frontend_root / full_path).resolve()
if full_path and requested.is_file() and frontend_root in requested.parents:
    return FileResponse(str(requested))
```

---

### 1.2 Frontend API Key Exposure Düzeltme
**Dosya:** `frontend/src/services/api.ts:8-11`
**Kaynak:** Claude, Codex, Gemini (3/3 review)
**Risk:** API key tarayıcı DevTools'tan görülebilir, write endpoint'lere yetkisiz erişim
**Efor:** 30 dakika

**Görevler:**
- [ ] `VITE_INTERNAL_API_KEY` kullanımını `api.ts`'den kaldır
- [ ] API key'i `sessionStorage` üzerinden runtime'da al (login prompt)
- [ ] 401/403 response'larda kullanıcıya key girişi sor (interceptor)
- [ ] `.env` dosyasından `VITE_INTERNAL_API_KEY` satırını kaldır

---

### 1.3 Runtime Bug: `SellerSnapshot.fetched_at` Yanlış Alan Adı
**Dosya:** `backend/app/api/store_product_routes.py:532`
**Kaynak:** Codex Review
**Risk:** Bu endpoint çağrıldığında `AttributeError` ile 500 hatası döner
**Efor:** 5 dakika

**Görevler:**
- [ ] `SellerSnapshot.fetched_at.desc()` → `SellerSnapshot.snapshot_date.desc()` olarak düzelt

**Önce:**
```python
.order_by(SellerSnapshot.fetched_at.desc()).first()
```
**Sonra:**
```python
.order_by(SellerSnapshot.snapshot_date.desc()).first()
```

---

### 1.4 Kritik Silent Failure: Job Status Güncellemesi
**Dosya:** `backend/app/api/url_scraper_routes.py:351-352`
**Kaynak:** Claude, Codex (2/3 review)
**Risk:** İç except'e düşerse job sonsuza kadar "running" kalır
**Efor:** 10 dakika

**Görevler:**
- [ ] `except: pass` → `except Exception as e: logger.critical(...)` olarak değiştir
- [ ] `db.rollback()` ekle
- [ ] Loglama ile debug edilebilir hale getir

---

## FAZA 2: Güvenlik İyileştirmeleri (P1)

### 2.1 SSL/TLS Doğrulamasını Etkinleştir
**Dosyalar:** 
- `backend/app/services/price_monitor_service.py` (3 yer)
- `backend/app/services/trendyol_price_monitor_service.py` (2 yer)
- `backend/app/services/transcript_service.py` (1 yer)
**Kaynak:** Claude, Codex (2/3 review)
**Risk:** Man-in-the-middle saldırısı ile veri manipülasyonu
**Efor:** 30 dakika

**Görevler:**
- [ ] `price_monitor_service.py`: 3 yerdeki `ssl.CERT_NONE` kaldır, default context kullan
- [ ] `trendyol_price_monitor_service.py`: 2 yerdeki `ssl.CERT_NONE` kaldır
- [ ] `transcript_service.py`: `session.verify = False` → `session.verify = True`
- [ ] Proxy üzerinden giden isteklerde SSL gerekliliğini test et
- [ ] Eğer bazı siteler self-signed cert kullanıyorsa, sadece o siteler için custom CA bundle kullan

---

### 2.2 Input Validation Ekle
**Dosyalar:**
- `backend/app/api/url_scraper_routes.py` (SingleUrlRequest)
- `backend/app/api/routes.py` (SearchRequest)
**Kaynak:** Claude, Codex (2/3 review)
**Risk:** SSRF saldırısı, aşırı uzun input ile hafıza sorunları
**Efor:** 30 dakika

**Görevler:**
- [ ] `SingleUrlRequest.url` → `HttpUrl` type'a çevir
- [ ] URL whitelist/blacklist: internal IP aralıklarını (127.x, 10.x, 169.254.x, 192.168.x) reddet
- [ ] `SearchRequest.keyword` → `Field(..., min_length=1, max_length=200)` ekle
- [ ] `SearchRequest.platform` → `Field(default="hepsiburada", pattern="^(hepsiburada|trendyol)$")` ekle
- [ ] Upload endpoint'lerinde dosya boyutu limiti standardize et

---

### 2.3 Redis Connection Pool Ekle
**Dosya:** `backend/app/main.py:49-65`
**Kaynak:** Gemini Review (benzersiz bulgu)
**Risk:** Yüksek trafikte port tükenmesi (EADDRINUSE)
**Efor:** 15 dakika

**Görevler:**
- [ ] Global `ConnectionPool` oluştur (modül seviyesinde)
- [ ] `_queue_reachable()` fonksiyonunda pool'dan bağlantı al
- [ ] `max_connections=10` limiti ekle

---

## FAZA 3: Bare Except ve Hata Yönetimi (P1)

### 3.1 scraping.py Bare Except Düzeltmeleri (17 yer)
**Dosya:** `backend/app/services/scraping.py`
**Kaynak:** Claude, Codex (2/3 review)
**Efor:** 1 saat

**Görevler (öncelik sırasıyla):**
- [ ] `satır 965`: Playwright selector timeout → `except Exception as e: logger.debug(...)`
- [ ] `satır 1114`: JSON-LD parse → `except (ValueError, KeyError) as e: logger.debug(...)`
- [ ] `satır 1137`: Float parse → `except (ValueError, TypeError): return None` + loglama
- [ ] `satır 571, 577`: Price parsing → spesifik exception + loglama
- [ ] `satır 1298, 1319, 1336`: İndirimli fiyat hesaplama → spesifik exception
- [ ] `satır 1390, 1481, 1488`: Veri extraction → spesifik exception
- [ ] `satır 1547`: Review extraction → `except Exception as e: logger.debug(...)`
- [ ] `satır 1615`: Human simulation → `except Exception as e: pass` (en az)
- [ ] `satır 1191, 1197, 1269`: Kalan bare except'ler → en az `except Exception:`
- [ ] Tüm `except:` → `except Exception:` olarak güncelle (BaseException yakalanmasın)

---

### 3.2 Diğer Dosyalardaki Bare Except Düzeltmeleri
**Dosyalar:**
- `backend/app/api/transcript_routes.py:366`
- `backend/app/core/config.py` (2 yer)
- `backend/app/main.py` (3 yer)
- `backend/app/services/category_scraper_service.py` (2 yer)
- `backend/app/api/routes.py` (2 yer)
- `backend/app/api/store_product_routes.py` (1 yer)
- `backend/app/services/url_scraper_service.py` (1 yer)
**Efor:** 45 dakika

**Görevler:**
- [ ] `transcript_routes.py:366`: `except:` → `except Exception as e: logger.error(...)`
- [ ] `config.py`: 2 yerdeki `except Exception:` → en az loglama ekle
- [ ] `main.py`: 3 yerdeki `except Exception:` → uygun loglama ekle
- [ ] Kalan dosyalardaki bare except'leri düzelt

---

## FAZA 4: Frontend UX İyileştirmeleri (P2)

### 4.1 Error Boundary Ekle
**Dosya:** `frontend/src/App.tsx`
**Kaynak:** Claude Review
**Efor:** 15 dakika

**Görevler:**
- [ ] `ErrorBoundary` class component oluştur
- [ ] `App` fonksiyonunu `ErrorBoundary` ile sar
- [ ] Hata durumunda kullanıcıya anlaşılır mesaj ve "Sayfayı Yenile" butonu göster

---

### 4.2 404 Sayfası Ekle
**Dosya:** `frontend/src/App.tsx`
**Kaynak:** Claude Review
**Efor:** 10 dakika

**Görevler:**
- [ ] `<Route path="*" element={<NotFound />} />` catch-all route ekle
- [ ] Basit 404 sayfası tasarla (Dashboard'a yönlendirme linki ile)

---

### 4.3 alert()/confirm() → Toast Sistemi
**Dosya:** `frontend/src/pages/PriceMonitor.tsx` (9 yer)
**Kaynak:** Claude, Codex (2/3 review)
**Efor:** 1 saat

**Görevler:**
- [ ] `react-hot-toast` veya benzeri minimal kütüphane ekle
- [ ] `PriceMonitor.tsx:238` → `toast.success(...)` 
- [ ] `PriceMonitor.tsx:244` → `toast.error(...)`
- [ ] `PriceMonitor.tsx:260, 271, 284, 309, 332` → `toast.error(...)`
- [ ] `PriceMonitor.tsx:289` → Custom confirm modal component
- [ ] `PriceMonitor.tsx:325` → `toast.info(...)`
- [ ] Diğer sayfalardaki alert/confirm kullanımlarını da tara ve değiştir

---

### 4.4 Erişilebilirlik (a11y) İyileştirmeleri
**Kaynak:** Claude, Codex (2/3 review)
**Efor:** 1 saat

**Görevler:**
- [ ] Tıklanabilir `div` → `button` veya `role="button"` + `tabIndex` ekle (`Sellers.tsx:243`)
- [ ] Görsellerde anlamlı `alt` text ekle (`ProductDetail.tsx:132`)
- [ ] Icon-only butonlara `aria-label` ekle
- [ ] Modal'larda ESC ile kapatma ekle (`PriceMonitor.tsx:932-975`)

---

## FAZA 5: Performans İyileştirmeleri (P2)

### 5.1 N+1 Query Düzeltmeleri
**Dosya:** `backend/app/api/routes.py`
**Kaynak:** Claude, Codex, Gemini (3/3 review)
**Efor:** 2 saat

**Görevler:**
- [ ] `routes.py:617`: `list_products` → `selectinload(Product.snapshots)` ekle
- [ ] `routes.py:746`: `analyze_products` → toplu sorgu ile düzelt
- [ ] `routes.py:1136`: Alert filter path → SQL-level filtreleme + pagination
- [ ] `routes.py:1262`: Diğer N+1 noktaları → eager loading ekle
- [ ] ORM model'lerinde `lazy="selectin"` default tanımla (`models.py`)

---

### 5.2 Frontend Performans
**Kaynak:** Claude, Codex, Gemini
**Efor:** 1.5 saat

**Görevler:**
- [ ] `PriceMonitor.tsx:810`: `Math.min(...sellers.map(...))` → `useMemo` ile cache'le
- [ ] Plotly.js lazy import veya code splitting (4.8MB chunk azaltma)
- [ ] Polling optimizasyonu: Task tamamlandığında polling durdur
- [ ] Büyük tablo/listelerde sanal listeleme (react-window/virtuoso) düşün

---

### 5.3 Async/Sync Uyumsuzluğu Giderme
**Dosya:** `backend/app/api/routes.py`
**Kaynak:** Claude Review
**Efor:** 30 dakika (kısa vadeli çözüm)

**Görevler:**
- [ ] Sync DB kullanan endpoint'leri `async def` → `def` olarak değiştir
- [ ] Veya: SQLAlchemy async engine'e geçiş planla (uzun vadeli, ayrı faz)

---

## FAZA 6: Kod Modülerliği / Refactoring (P2)

### 6.1 routes.py Bölme (2144 satır → ~5-6 dosya)
**Dosya:** `backend/app/api/routes.py`
**Kaynak:** Claude, Codex, Gemini (3/3 review)
**Efor:** 2-3 saat

**Görevler:**
- [ ] `price_monitor_routes.py` oluştur: /price-monitor/* endpoint'lerini taşı
- [ ] `product_routes.py` oluştur: /products/* endpoint'lerini taşı
- [ ] `search_routes.py` oluştur: /search, /tasks endpoint'lerini taşı
- [ ] `seller_routes.py` oluştur: /sellers/* endpoint'lerini taşı
- [ ] `stats_routes.py` oluştur: /stats, /analyze endpoint'lerini taşı
- [ ] Pydantic modelleri `schemas/` dizinine ayır
- [ ] `main.py`'de yeni router'ları kaydet
- [ ] Tüm endpoint'lerin çalıştığını doğrula

---

### 6.2 api.ts Bölme (1051 satır → ~5-6 dosya)
**Dosya:** `frontend/src/services/api.ts`
**Kaynak:** Claude, Codex (2/3 review)
**Efor:** 1-2 saat

**Görevler:**
- [ ] `services/api/client.ts` oluştur: Axios instance + interceptors
- [ ] `services/api/types.ts` oluştur: Tüm interface/type tanımları
- [ ] `services/api/products.ts` oluştur: Product API fonksiyonları
- [ ] `services/api/priceMonitor.ts` oluştur: Price Monitor API fonksiyonları
- [ ] `services/api/sellers.ts` oluştur: Seller API fonksiyonları
- [ ] `services/api/search.ts` oluştur: Search API fonksiyonları
- [ ] `services/api/index.ts` oluştur: Re-export barrel file
- [ ] Tüm sayfa komponentlerindeki import'ları güncelle

---

### 6.3 PriceMonitor.tsx Bölme (1010 satır → alt komponentler)
**Dosya:** `frontend/src/pages/PriceMonitor.tsx`
**Kaynak:** Claude Review
**Efor:** 2 saat

**Görevler:**
- [ ] `usePriceMonitor.ts` custom hook oluştur (state + logic)
- [ ] `PriceMonitorHeader.tsx` oluştur (platform seçimi, aksiyon butonları)
- [ ] `ProductList.tsx` oluştur (ürün listesi + filtreleme)
- [ ] `SellerPanel.tsx` oluştur (satıcı detayları)
- [ ] `ImportModal.tsx` oluştur (JSON import modal)
- [ ] `DeleteConfirmModal.tsx` oluştur (silme onay modal)

---

### 6.4 scraping.py Refactoring (1633 satır)
**Dosya:** `backend/app/services/scraping.py`
**Kaynak:** Claude Review
**Efor:** 2-3 saat

**Görevler:**
- [ ] Price parsing utility fonksiyonu oluştur (DRY - ~15 tekrar)
- [ ] `_fetch_with_scraperapi_proxy` ve `_fetch_with_scraperapi` birleştir
- [ ] HTTP fetch, HTML parsing, data extraction ayrı modüllere böl
- [ ] Anti-detection fonksiyonlarını ayrı dosyaya taşı

---

## FAZA 7: Altyapı ve Tooling (P2)

### 7.1 Alembic Migration Ekle
**Dosya:** `backend/app/main.py:18`
**Kaynak:** Claude, Codex (2/3 review)
**Efor:** 1 saat

**Görevler:**
- [ ] `alembic` paketini requirements.txt'e ekle
- [ ] `alembic init alembic` ile başlat
- [ ] `alembic/env.py`'de `target_metadata = Base.metadata` ayarla
- [ ] İlk migration oluştur: `alembic revision --autogenerate -m "initial"`
- [ ] `Base.metadata.create_all()` satırını kaldır veya sadece dev ortamında çalışacak şekilde ayarla
- [ ] README'ye migration komutlarını ekle

---

### 7.2 Temel Test Altyapısı Kur
**Kaynak:** Claude, Codex (2/3 review)
**Efor:** 3-4 saat

**Görevler:**
- [ ] `pytest` + `pytest-asyncio` + `httpx` ekle (backend)
- [ ] `backend/tests/` dizini oluştur
- [ ] `conftest.py` → test DB fixture, test client
- [ ] Kritik endpoint'ler için temel testler: `/health`, `/api/products`, `/api/search`
- [ ] Güvenlik testleri: path traversal denemesi, SSRF denemesi
- [ ] Frontend: `vitest` ekle ve en az 1 komponent testi yaz

---

## FAZA 8: Temizlik ve Dokümantasyon (P3)

### 8.1 Repo Temizliği
**Kaynak:** Claude Review
**Efor:** 15 dakika

**Görevler:**
- [ ] `hepsiburada_active_products.json` (1.7MB) → `.gitignore`'a ekle ve repodan kaldır
- [ ] `attached_assets/` → `.gitignore`'a ekle
- [ ] `backend/.env` → `.gitignore`'da olduğunu doğrula (doğrulanmış ✓)
- [ ] Deploy ortamında `DEBUG_SAVE_HTML=false` olduğunu doğrula

---

### 8.2 İsimlendirme ve Dokümantasyon Tutarlılığı
**Kaynak:** Claude, Codex, Gemini
**Efor:** 1 saat

**Görevler:**
- [ ] `config.py`: `SCRAPPER_API` / `SCRAPPPER_API` typo'larına açıklayıcı yorum ekle
- [ ] Kod içi yorumları Türkçe veya İngilizce olarak standardize et (birini seç)
- [ ] `CategoryExplorer.tsx`: `ssGet`, `ssSet`, `ssGetJson` → anlaşılır isimlerle değiştir
- [ ] README'deki `PRICE_MONITOR_MAX_CONCURRENT_REQUESTS` değerini (17) → kodla uyumlu (40) güncelle
- [ ] Swagger/OpenAPI docs özelleştir (endpoint açıklamaları ekle)

---

### 8.3 npm Audit Zafiyetleri
**Kaynak:** Codex Review
**Efor:** 30 dakika

**Görevler:**
- [ ] `npm audit` çalıştır ve sonuçları incele
- [ ] 14 zafiyet (2 moderate, 12 high) → güncellenebilir paketleri güncelle
- [ ] Güncellenemeyen paketler için `npm audit fix --force` veya alternatif paket ara

---

## Özet: Efor Tahmini

| Faz | Açıklama | Tahmini Efor | Öncelik |
|-----|----------|-------------|---------|
| 1 | Kritik Güvenlik + Bug Fix | ~1 saat | P0 |
| 2 | Güvenlik İyileştirmeleri | ~1.5 saat | P1 |
| 3 | Bare Except Düzeltmeleri | ~1.5 saat | P1 |
| 4 | Frontend UX | ~2.5 saat | P2 |
| 5 | Performans | ~4 saat | P2 |
| 6 | Kod Modülerliği | ~9 saat | P2 |
| 7 | Altyapı (Migration, Test) | ~5 saat | P2 |
| 8 | Temizlik ve Dokümantasyon | ~2 saat | P3 |
| **Toplam** | | **~27 saat** | |

---

## Uygulama Sırası Önerisi

```
Hafta 1: Faz 1 (P0) + Faz 2 (P1) + Faz 3 (P1)
Hafta 2: Faz 4 (UX) + Faz 5 (Performans)  
Hafta 3: Faz 6 (Refactoring)
Hafta 4: Faz 7 (Altyapı) + Faz 8 (Temizlik)
```

---

*Bu plan 3 bağımsız code review raporundan (Claude Opus, Codex, Gemini) derlenerek oluşturulmuştur.*
*Son güncelleme: 2026-02-22*
