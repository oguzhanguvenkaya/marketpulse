# MarketPulse MVP Master Plan

**Tarih:** 2026-02-27 (güncellendi)
**Strateji:** Dikey Derinlik (Price Monitor odaklı SaaS → Kârlılık Yönetim Platformu)
**Zaman Çerçevesi:** 19+ hafta (7 faz — MVP Faz 0-3, Pro Faz 4-6)
**Hedef:** Ödeme yapan ilk 50 müşteri (Faz 1 sonunda), 200+ müşteri (Faz 3 sonunda)

---

## Context

MarketPulse, Türk e-ticaret pazaryerlerinden (Hepsiburada, Trendyol) ürün verisi toplayan, fiyat izleyen ve AI destekli insight sunan bir veri analiz platformu. Proje teknik olarak çalışır durumda ancak SaaS olarak satışa hazır değil.

**4 uzman incelemesi sonucu:**
- Business Analyst: MVP %42 hazır — auth, billing, alarm, zamanlama eksik
- Fullstack Dev: Backend 6.5/10, Frontend 7.5/10 — multi-tenant yok, test %10
- UI/UX Designer: 5.4/10 — landing page, onboarding, conversion akışı yok
- Scraping Expert: 4.5/10 genel, 7/10 fiyat izleme — CSS selector kırılgan, modülerlik 3/10

**Güçlü yanlar:** HB Campaign API (rakiplerde yok), Price Monitor API tabanlı, iyi frontend component ayrışımı.

---

## FAZ 0 — Temel Altyapı (Hafta 1-3)

> **Hedef:** Auth, multi-tenant izolasyon, marketplace adapter mimarisi, otomatik zamanlama ve kritik teknik borç temizliği. Bu faz olmadan hiçbir şey satılamaz.

### Mevcut Durum Özeti (Kod Analizi)
- **Auth:** Tek `INTERNAL_API_KEY` ile HMAC doğrulama (`security.py`, 28 satır). GET endpoint'leri tamamen açık. Kullanıcı kavramı yok.
- **DB:** 15 model (`models.py`, 443 satır), hiçbirinde `user_id` yok. Tüm veri global erişimli.
- **Celery:** 2 task (`tasks.py`, 223 satır): `run_scraping_task` ve `run_price_monitor_fetch_task`. Beat konfigürasyonu yok, sadece manuel tetikleme.
- **Frontend:** 14 route (`App.tsx`, 66 satır), hepsi public. Auth context yok, protected route yok. API key `sessionStorage`'da.
- **Scraping:** CSS selector'lar kodun içinde hardcoded. HB Listings API + Campaign API (`price_monitor_service.py`, 800+ satır). TY SSR JSON regex (`trendyol_price_monitor_service.py`, 700+ satır).

---

### 0.1 Auth Sistemi (Supabase Auth)
**Efor:** 4-5 gün | **Öncelik:** CRITICAL | **Bağımlılık:** Yok (ilk yapılmalı)

**Mevcut → Hedef:**
- `security.py` (28 satır, tek API key) → Supabase JWT doğrulama middleware
- `client.ts` (91 satır, sessionStorage API key) → Supabase JS SDK ile token yönetimi
- `App.tsx` (66 satır, tüm route'lar public) → ProtectedRoute wrapper

**Backend Değişiklikler:**

1. **Supabase JWT Middleware** — Her request'te `Authorization: Bearer <token>` header'ından JWT decode ve user_id çıkarma
   ```python
   # backend/app/core/auth.py (YENİ)
   async def get_current_user(request: Request, db: Session) -> User:
       token = request.headers.get("Authorization", "").replace("Bearer ", "")
       payload = verify_supabase_jwt(token)  # python-jose ile
       user = db.query(User).filter(User.id == payload["sub"]).first()
       if not user: raise HTTPException(401)
       return user
   ```

2. **Route dependency değişikliği** — `Depends(require_mutating_api_key)` → `Depends(get_current_user)`
   - Değişecek: `price_monitor_routes.py` router dependency (satır 1-10)
   - Değişecek: `search_routes.py`, `seller_routes.py`, `product_routes.py` router dependency
   - Tüm GET endpoint'leri de artık auth gerektirecek

3. **Supabase proje kurulumu** — Supabase dashboard'da proje oluştur, env vars ekle:
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`

**Frontend Değişiklikler:**

4. **AuthContext** — Supabase JS SDK ile session yönetimi
   ```typescript
   // frontend/src/contexts/AuthContext.tsx (YENİ)
   // supabase.auth.onAuthStateChange() listener
   // user, session, loading, signIn(), signUp(), signOut()
   ```

5. **Login/Register sayfaları** — Email/password + Google OAuth
   - `frontend/src/pages/Login.tsx` (YENİ)
   - `frontend/src/pages/Register.tsx` (YENİ)
   - `frontend/src/pages/ForgotPassword.tsx` (YENİ)

6. **API Client güncelleme** — `client.ts`'deki `X-API-Key` interceptor → `Authorization: Bearer` interceptor
   - Mevcut: `sessionStorage.getItem('mp_api_key')` → Kaldır
   - Yeni: `supabase.auth.getSession()` → `config.headers['Authorization'] = 'Bearer ' + session.access_token`
   - `ApiKeyModal` component → Kaldır

7. **Protected Routes** — `App.tsx`'e ProtectedRoute wrapper
   ```typescript
   // Auth sayfaları: /login, /register, /forgot-password (public)
   // Uygulama: /app/* prefix altında (protected)
   // Landing: / (public — Faz 1'de eklenecek, şimdilik /login'e redirect)
   ```

**Dosyalar:**
| Dosya | İşlem | Detay |
|-------|-------|-------|
| `backend/app/core/auth.py` | YENİ | Supabase JWT verify, get_current_user dependency |
| `backend/app/core/security.py` | DEĞİŞECEK | require_mutating_api_key kaldırılacak |
| `backend/app/main.py` | DEĞİŞECEK | CORS "Authorization" header zaten var, env check ekle |
| `frontend/src/contexts/AuthContext.tsx` | YENİ | Supabase auth state management |
| `frontend/src/pages/Login.tsx` | YENİ | Login formu |
| `frontend/src/pages/Register.tsx` | YENİ | Kayıt formu |
| `frontend/src/services/client.ts` | DEĞİŞECEK | X-API-Key → Bearer token, ApiKeyModal event kaldır |
| `frontend/src/App.tsx` | DEĞİŞECEK | ProtectedRoute, /app prefix, auth routes |
| `frontend/src/components/ApiKeyModal.tsx` | SİLİNECEK | Artık gereksiz |

**Test:**
- [ ] Email/password ile kayıt ve giriş çalışıyor
- [ ] JWT token otomatik yenileniyor (Supabase handles)
- [ ] Yetkisiz istek 401 dönüyor
- [ ] Frontend login sayfasına yönlendiriyor

---

### 0.2 Multi-Tenant DB Migration
**Efor:** 3-4 gün | **Öncelik:** CRITICAL | **Bağımlılık:** 0.1 (User modeli gerekli)

**Mevcut → Hedef:**
- 15 model, 0 user_id → Tüm modellere `user_id` ekleme
- Global query (`db.query(X).all()`) → Filtrelenmiş query (`db.query(X).filter(X.user_id == user.id)`)

**Adım 1: Yeni tablolar (Alembic migration)**

```python
# users tablosu (Supabase auth ile senkron)
class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True)          # Supabase auth.users.id ile aynı
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    plan_tier = Column(String, default="free")    # free, starter, pro, enterprise
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# subscriptions tablosu (Faz 1 Stripe ile doldurulacak, şimdi iskelet)
class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), unique=True)
    plan_tier = Column(String, default="free")
    status = Column(String, default="active")     # active, canceled, past_due
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    sku_limit = Column(Integer, default=10)
    scan_frequency = Column(Integer, default=1)   # günlük tarama sayısı
    created_at = Column(DateTime, server_default=func.now())
```

**Adım 2: user_id kolonu ekleme (15 tablo)**

MVP-kritik tablolar (öncelik sırasıyla):
| Tablo | Notlar |
|-------|--------|
| `monitored_products` | `user_id + platform + sku` UNIQUE constraint |
| `seller_snapshots` | Cascade: monitored_product silinirse snapshot da silinsin |
| `price_monitor_tasks` | user_id ile task izolasyonu |
| `search_tasks` | user_id filtresi |
| `products` | search_task üzerinden dolaylı user_id |
| `category_sessions` | user_id filtresi |
| `category_products` | session üzerinden dolaylı |
| `scrape_jobs` | user_id filtresi |
| `store_products` | user_id filtresi |
| `json_files` | user_id filtresi |
| `transcript_jobs` | user_id filtresi |

**Migration stratejisi:**
```python
# Alembic migration — 2 aşamalı (mevcut veri varsa)
# Aşama 1: user_id nullable olarak ekle
op.add_column('monitored_products', sa.Column('user_id', UUID, nullable=True))
# Aşama 2: default user oluştur, mevcut veriyi ata, NOT NULL yap
op.execute("UPDATE monitored_products SET user_id = '<default-user-uuid>' WHERE user_id IS NULL")
op.alter_column('monitored_products', 'user_id', nullable=False)
op.create_foreign_key(...)
```

**Adım 3: Query filtresi (tüm route dosyaları)**

```python
# Her route'a user dependency eklenir
async def get_products(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    products = db.query(MonitoredProduct)\
        .filter(MonitoredProduct.user_id == user.id)\
        .filter(MonitoredProduct.platform == platform).all()
```

**Adım 4: Index ekleme**
```sql
CREATE INDEX ix_monitored_products_user_platform ON monitored_products(user_id, platform, is_active);
CREATE INDEX ix_price_monitor_tasks_user ON price_monitor_tasks(user_id);
CREATE INDEX ix_search_tasks_user ON search_tasks(user_id);
CREATE INDEX ix_seller_snapshots_product ON seller_snapshots(monitored_product_id, fetched_at DESC);
```

**Dosyalar:**
| Dosya | İşlem |
|-------|-------|
| `backend/app/db/models.py` | DEĞİŞECEK — User, Subscription modeli ekle, tüm modellere user_id |
| `backend/alembic/versions/xxx_add_multi_tenant.py` | YENİ — Migration dosyası |
| `backend/app/api/price_monitor_routes.py` | DEĞİŞECEK — Tüm query'lere user filtresi |
| `backend/app/api/search_routes.py` | DEĞİŞECEK — user filtresi |
| `backend/app/api/seller_routes.py` | DEĞİŞECEK — user filtresi |
| `backend/app/api/product_routes.py` | DEĞİŞECEK — user filtresi |
| `backend/app/api/stats_routes.py` | DEĞİŞECEK — user filtresi |

**Test:**
- [ ] Migration başarılı (up + down)
- [ ] User A'nın verisi User B'ye görünmüyor
- [ ] Mevcut veriler default user'a atanmış
- [ ] Composite index'ler query planında kullanılıyor

---

### 0.3 Marketplace Adapter Mimarisi
**Efor:** 5-7 gün | **Öncelik:** HIGH | **Bağımlılık:** Yok (paralel yapılabilir)

**Hedef:** Modüler adapter pattern — yeni pazaryeri (Amazon, N11) eklemek 1-2 gün sürmeli.

**Yeni Dizin Yapısı:**
```
backend/app/marketplaces/
├── __init__.py
├── base.py                      # BaseMarketplaceAdapter (ABC)
├── registry.py                  # MarketplaceRegistry — get_adapter("hepsiburada")
├── types.py                     # SellerPrice, SearchResult, ProductData, CategoryData
├── config/
│   ├── hepsiburada.yaml         # API URL'leri, selector'lar, tag pattern'ları
│   └── trendyol.yaml            # SSR JSON key'leri, selector'lar
├── hepsiburada/
│   ├── __init__.py
│   ├── price_adapter.py         # Listings API + Campaign API
│   ├── search_adapter.py        # Arama parsing
│   ├── product_adapter.py       # Ürün detay parsing
│   └── category_adapter.py      # Kategori parsing
└── trendyol/
    ├── __init__.py
    ├── price_adapter.py         # SSR JSON parsing
    ├── search_adapter.py        # Arama
    ├── product_adapter.py       # Ürün detay
    └── category_adapter.py      # Kategori
```

**BaseMarketplaceAdapter interface:**
```python
class BaseMarketplaceAdapter(ABC):
    platform: str
    config: dict  # YAML'dan yüklenen config

    @abstractmethod
    async def get_seller_prices(self, sku: str, http_session) -> List[SellerPrice]: ...

    @abstractmethod
    async def search_products(self, keyword: str, max_results: int) -> SearchResult: ...

    @abstractmethod
    async def get_product_detail(self, url: str) -> ProductData: ...

    @abstractmethod
    async def parse_category(self, url: str, max_pages: int) -> CategoryData: ...
```

**Taşıma stratejisi:** Mevcut logic'i yeni adapter dosyalarına taşı, hardcoded değerleri YAML'a al, facade pattern ile mevcut service'leri adapter'a yönlendir. Davranış değişmeden refactoring.

**Mevcut koddan taşınacak kritik logic:**
| Kaynak | Hedef |
|--------|-------|
| `price_monitor_service.py` → fetch_all_products, fetch_campaign_price | `hepsiburada/price_adapter.py` |
| `trendyol_price_monitor_service.py` → parse_merchants_from_json | `trendyol/price_adapter.py` |
| `scraping.py` → scrape_hepsiburada_search, scrape_trendyol_search | `*/search_adapter.py` |
| `category_scraper_service.py` → parse_hepsiburada_category | `hepsiburada/category_adapter.py` |

---

### 0.4 Otomatik Zamanlama (Dual Executor: Local + Celery)
**Efor:** 3-4 gün | **Öncelik:** HIGH | **Bağımlılık:** 0.1 + 0.2

**Dual-Executor Stratejisi:**
```
Replit (Faz 0-1):
  └── PRICE_MONITOR_EXECUTOR=local
  └── Zamanlama: FastAPI lifespan background loop (her 30 dk)
  └── Upstash Redis: Celery testi için hazır ama zorunlu değil

GCP Cloud Run (Faz 2+):
  ├── API: PRICE_MONITOR_EXECUTOR=celery
  ├── Worker: Celery worker (min 1 instance)
  ├── Cloud Scheduler → HTTP trigger (Beat yerine — autoscale-safe)
  └── Upstash Redis: Broker
```

**Yapılacaklar:**
1. `ScheduledTask` modeli (user_id, platform, frequency_hours, next_run_at)
2. `SchedulerService` — executor-agnostic dispatch (local: asyncio, celery: send_task)
3. FastAPI lifespan background loop (local mode)
4. Celery config Upstash Redis TLS desteği
5. `POST /api/scheduler/dispatch` endpoint (Cloud Scheduler trigger)
6. Task deduplication (DB advisory lock)

---

### 0.5 Email Alarm Sistemi
**Efor:** 2-3 gün | **Öncelik:** HIGH | **Bağımlılık:** 0.1 + 0.4

**Yapılacaklar:**
1. Resend email entegrasyonu (`RESEND_API_KEY` mevcut)
2. Alarm tetikleme: price fetch sonrası threshold kontrolü
3. Email template'leri (Türkçe): fiyat değişimi, buybox kaybı, kampanya uyarısı
4. Kullanıcı alarm tercihleri (email on/off, frequency)
5. AlertLog tablosu (gönderim kaydı)

---

### 0.6 Kritik Teknik Borç Temizliği
**Efor:** 3-4 gün | **Öncelik:** MEDIUM | **Bağımlılık:** 0.2 ile birlikte

| # | Sorun | Dosya | Efor |
|---|-------|-------|------|
| 1 | N+1 query — export endpoint | `price_monitor_routes.py:400-476` | 0.5 gün |
| 2 | N+1 query — alert filter (RAM) | `price_monitor_routes.py:278-359` | 1 gün |
| 3 | Bulk delete ORM loop → SQL DELETE | `price_monitor_routes.py:611-641` | 0.5 gün |
| 4 | SSL verify=False → MITM riski | `price_monitor_service.py:159` | 0.5 gün |
| 5 | Data retention yok (snapshots büyüyor) | `seller_snapshots` | 0.5 gün |
| 6 | Unique constraint eksik | `models.py` | 0.5 gün |

---

### Faz 0 Uygulama Sırası

```
Hafta 1:
  [0.1] Auth Sistemi ──────────────┐
  [0.3] Marketplace Adapter ───┐   │  (paralel)
                               │   │
Hafta 2:                       │   │
  [0.2] Multi-Tenant DB ◄─────┘───┘  (0.1 bitmeli)
  [0.3] Adapter devam ────────────┐
                                  │
Hafta 3:                          │
  [0.4] Celery Beat ◄────────────┘  (0.2 bitmeli)
  [0.5] Email Alarm                  (0.1 + 0.4 bitmeli)
  [0.6] Teknik Borç                  (0.2 ile birlikte)
```

**Kritik Yol:** 0.1 (Auth) → 0.2 (Multi-tenant) → 0.4 (Celery) → 0.5 (Email)
**Paralel:** 0.3 (Adapter) herhangi bir anda başlayabilir

---

## FAZ 1 — Satışa Hazırlık (Hafta 4-7)

> **Hedef:** İlk ödeme yapan müşteriyi kabul edebilecek duruma gelmek.

### 1.1 Stripe SaaS Abonelik (5-6 gün)
- Stripe Checkout Session, webhook handler, plan tier middleware
- Plan limitleri: Free(10 SKU) / Starter 299₺(200) / Pro 899₺(1000) / Enterprise

### 1.2 Landing Page + Pricing (5-7 gün)
- Marketing landing page `/`, app `/app` prefix'ine taşıma
- Hero, feature showcase, pricing kartları, CTA
- Tailwind tema borcu temizliği (280 hardcoded renk)

### 1.3 Onboarding Wizard (3-4 gün)
- 6 adımlı wizard: platform seçimi → SKU ekle → threshold → tarama → alarm → dashboard

### 1.4 CSV/Excel Import (2-3 gün)
- Backend parse endpoint, kolon eşleştirme, drag & drop upload

### 1.5 Fiyat Geçmişi Grafikleri (3-4 gün)
- Price history endpoint, sparkline/lightweight-charts, Plotly optimize

### 1.6 Kârlılık Simülatörü *(plan_2.md)* (3-4 gün)
- Net kâr formülü: Satış - Maliyet - Komisyon - Kargo
- Waterfall grafiği, zarar uyarısı, kârlılık badge

### 1.7 MVP Navigasyon Sadeleştirme (2 gün)
- Sidebar: Dashboard, Price Monitor, Keyword Search, Sellers, Settings
- Pro feature'ları gizle

---

## FAZ 2 — AI + UX Zenginleştirme (Hafta 8-10)

> **Hedef:** AI chatbot ile farklılaşma, rakip satıcı takibi, dashboard yenileme.

### 2.1 AI Chatbot — Tool-Calling Mimarisi (7-8 gün)
- OpenAI tool-calling, 8 read-only tool, streaming, floating chat panel

### 2.2 Rakip Satıcı Takibi (4-5 gün)
- Satıcı ekleme, ürün listesi çekme, karşılaştırma tablosu

### 2.3 Keyword Araması İyileştirme (3-4 gün)
- İlk N ürün, kategori bilgisi, keyword geçmişi

### 2.4 Category Analyzer *(plan_2.md)* (4-5 gün)
- AI ile kategori uyum denetimi, yanlış kategori uyarısı

### 2.5 Dashboard Yenileme (3-4 gün)
- İş değeri metrikleri, alarm kartları, kârlılık özeti

---

## FAZ 3 — Büyüme & Genişleme (Hafta 11-13)

> **Hedef:** Amazon TR + N11, AI agent, raporlama, marketplace API.

### 3.1 Amazon TR + N11 Adapters (7-10 gün)
### 3.2 AI Agent — Aksiyon Alabilen (4-5 gün)
### 3.3 AI-Destekli Generic Web Scraping (5-6 gün)
### 3.4 Raporlama (3-4 gün)
### 3.5 Marketplace API Entegrasyonu (3-4 gün)
### 3.6 Kampanya Fırsat Merkezi *(plan_2.md)* (3-4 gün)

---

## FAZ 4 — Kârlılık Otomasyonu *(plan_2.md)* (Hafta 14-16)

> **Hedef:** Kullanıcı ekran başında değilken kârlılığını koruyan otomasyon kuralları.

### 4.1 Kırmızı Çizgi Otomasyonu (5-7 gün)
- Min kâr marjı kuralı, dry-run, otomatik aksiyon

### 4.2 Trend/Rota Tabanlı Reklam Kelimesi Önerisi (3-4 gün)
- HB Rota / TY Trend verileri, keyword eşleştirme

---

## FAZ 5 — AI Müşteri Hizmetleri *(plan_2.md)* (Hafta 17-18)

> **Hedef:** Pazaryeri müşteri sorularına AI ile otonom yanıt.

### 5.1 Müşteri Soruları Polling (3-4 gün)
### 5.2 AI Yanıt Üretimi ve Onay Akışı (4-5 gün)
- Copilot Modu + Autopilot Modu

---

## FAZ 6 — İleri Özellikler (Hafta 19+)

- Ajans paketleri, marka/bayi takip, marketplace API tam entegrasyon, mobile app

---

## Deployment Stratejisi

### Faz 0-1: Replit Autoscale (mevcut)
- `PRICE_MONITOR_EXECUTOR=local` — in-process async tasks
- Zamanlama: FastAPI lifespan background loop
- Upstash Redis: .env'de hazır, opsiyonel Celery testi için
- DB: Neon PostgreSQL (mevcut)

### Faz 2-3: GCP Cloud Run'a geçiş
```
Cloud Run: marketpulse-api (autoscale 0→N)
Cloud Run: marketpulse-worker (Celery, min 1)
Cloud Scheduler (Beat yerine — autoscale-safe)
Upstash Redis (broker)
Neon PostgreSQL (değişmez)
Secret Manager (API keys)
```

gcloud CLI ile yönetim, GitHub Actions CI/CD.

---

## Teknik Kararlar Özeti

| Karar | Seçim | Neden |
|-------|-------|-------|
| Auth | Supabase Auth | Hızlı, güvenli, PostgreSQL native |
| Billing | Stripe Subscriptions | SaaS standardı, webhook desteği |
| AI | OpenAI tool-calling | Baştan doğru mimari, genişletilebilir |
| Scraping | Marketplace Adapter pattern | Modüler, yeni platform kolayca eklenir |
| Email | Resend | Geliştirici dostu, ucuz, iyi API |
| Task Queue | Upstash Redis + Celery | Serverless Redis, autoscale uyumlu |
| Deploy (başlangıç) | Replit | Mevcut, çalışıyor |
| Deploy (büyüme) | GCP Cloud Run | Container, auto-scale, maliyet etkin |
| Frontend | Mevcut React+Vite (değişmez) | Yeniden yazma gereksiz |
| DB | Neon PostgreSQL (devam) | Mevcut, serverless, iyi çalışıyor |

---

## Doğrulama Planı

### Faz 0 Doğrulama
- [ ] Supabase Auth ile kayıt/giriş çalışıyor
- [ ] Farklı kullanıcılar farklı veriler görüyor (multi-tenant)
- [ ] Marketplace adapter ile mevcut HB/TY fiyat izleme çalışıyor
- [ ] Otomatik zamanlama çalışıyor (scheduler loop)
- [ ] Threshold ihlalinde email geliyor
- [ ] N+1 query düzeltmeleri — sayfa yüklemesi <3sn
- [ ] Mevcut testler geçiyor + yeni testler eklendi

### Faz 1 Doğrulama
- [ ] Stripe ile ödeme yapılabiliyor
- [ ] Plan limitleri uygulanıyor
- [ ] Landing page live, SEO meta tags doğru
- [ ] Onboarding tamamlanabiliyor
- [ ] CSV import çalışıyor
- [ ] Fiyat geçmişi grafiği gösteriliyor

### Faz 2 Doğrulama
- [ ] AI chatbot sorulara doğru yanıt veriyor
- [ ] Rakip satıcı eklenip verileri görülebiliyor
- [ ] Category Analyzer doğru/yanlış kategori tespit ediyor
- [ ] Dashboard iş değeri metrikleri gösteriyor

### Faz 3 Doğrulama
- [ ] Amazon TR + N11 adapter çalışıyor
- [ ] AI agent aksiyon alabiliyor (onay ile)
- [ ] Kampanya Fırsat Merkezi çalışıyor
- [ ] GCP Cloud Run'da canlı çalışıyor

### Faz 4 Doğrulama
- [ ] Kırmızı çizgi kuralı tanımlanıp aktif ediliyor
- [ ] Kural ihlalinde otomatik aksiyon çalışıyor
- [ ] Trend kelime-ürün eşleştirmesi doğru yapılıyor

### Faz 5 Doğrulama
- [ ] Müşteri soruları polling ediliyor
- [ ] AI yanıtı hallüsinasyon yapmadan üretiliyor
- [ ] Copilot modunda onay/düzenleme yapılabiliyor

---

## Efor Özeti

| Faz | Süre | Toplam İş Günü |
|-----|------|---------------|
| Faz 0 — Altyapı | Hafta 1-3 | ~20-25 gün |
| Faz 1 — Satışa Hazırlık | Hafta 4-7 | ~23-30 gün |
| Faz 2 — AI + UX | Hafta 8-10 | ~22-26 gün |
| Faz 3 — Büyüme | Hafta 11-13 | ~25-33 gün |
| Faz 4 — Kârlılık Otomasyonu | Hafta 14-16 | ~8-11 gün |
| Faz 5 — AI Müşteri Hizmetleri | Hafta 17-18 | ~7-9 gün |
| Faz 6 — İleri Özellikler | Hafta 19+ | Belirsiz (vizyon) |
| **MVP TOPLAM (Faz 0-3)** | **13 hafta** | **~90-114 iş günü** |
| **PRO DAHİL (Faz 0-5)** | **18 hafta** | **~105-134 iş günü** |

> Not: Tek geliştirici varsayımıyla. Paralel çalışma ile toplam süre %30-40 kısaltılabilir.
