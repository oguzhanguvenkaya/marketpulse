# MarketPulse iOS — Backend Gereksinimleri Dokümanı

> Bu doküman, iOS mobil uygulamasının backend'e bağlanması için gereken tüm konfigürasyon, credential ve endpoint bilgilerini içerir.
> LLM Agent'ın Xcode projesini konfigüre ederken referans alacağı tek kaynak belgedir.

---

## 1. KONFIGÜRASYON (iOS Tarafı)

### 1.1 API Base URL

Backend FastAPI uygulaması `0.0.0.0:8000` portunda çalışıyor.

| Ortam | URL | Kullanım |
|-------|-----|----------|
| **Debug (Simulator)** | `http://localhost:8000` | Xcode Simulator'da geliştirme |
| **Debug (Physical Device)** | `http://<mac-ip>:8000` | Fiziksel cihazda geliştirme |
| **Staging** | Henüz yok | GCP Cloud Run'a deploy sonrası |
| **Production** | Henüz yok | GCP Cloud Run'a deploy sonrası |

**Xcode'da tanımlama yöntemi:**

```swift
// Configuration.swift
enum Configuration {
    enum API {
        #if DEBUG
        static let baseURL = "http://localhost:8000"
        #else
        static let baseURL = "https://api.marketpulse.com" // Production deploy sonrası güncellenecek
        #endif
    }
}
```

**Önemli:** Frontend şu an `/api` prefix'i ile relative çağrı yapıyor (`baseURL: '/api'`). iOS'ta ise full URL kullanılacak: `http://localhost:8000/api/...`

### 1.2 Info.plist — App Transport Security

Debug build'de HTTP localhost'a izin vermek için:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <false/>
    <key>NSExceptionDomains</key>
    <dict>
        <key>localhost</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
            <key>NSTemporaryExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
</dict>
```

> **Production build'de:** `NSExceptionDomains` kaldırılacak, tüm bağlantılar HTTPS olacak.

### 1.3 CORS Ayarı (Backend Tarafı)

Mevcut CORS konfigürasyonu (`backend/app/core/config.py:86`):

```python
CORS_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
```

**iOS için CORS sorunu yok** — iOS native HTTP çağrıları browser CORS politikasına tabi değil. `URLSession` çağrıları doğrudan backend'e gider, Origin header göndermez. Yani **backend'de CORS değişikliği gerekmez.**

---

## 2. SUPABASE AUTH KONFİGÜRASYONU

### 2.1 Supabase Proje Bilgileri

Mevcut `.env` dosyasından (`/Users/projectx/Desktop/marketpulse/.env`):

| Değişken | Değer | iOS'ta Kullanım |
|----------|-------|-----------------|
| `SUPABASE_URL` | `https://xxgvnqnykkbkhjdnizge.supabase.co` | Auth API base URL |
| `SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4Z3ZucW55a2tia2hqZG5pemdlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIxNzgxNDEsImV4cCI6MjA4Nzc1NDE0MX0.8EnpfifsIXkX0OLTnEdE0eMMXwhIKJHQYLR_Bof0M60` | Auth API key (apikey header) |

> **SUPABASE_SERVICE_ROLE_KEY ve JWT_SECRET iOS'ta KULLANILMAYACAK** — bunlar sadece backend tarafında kullanılır.

### 2.2 Auth Endpoint'leri (Supabase GoTrue API)

**Base URL:** `https://xxgvnqnykkbkhjdnizge.supabase.co/auth/v1`

**Gerekli Header'lar (tüm auth isteklerinde):**

```
apikey: <SUPABASE_ANON_KEY>
Content-Type: application/json
```

#### 2.2.1 Login (Email/Password)

```
POST https://xxgvnqnykkbkhjdnizge.supabase.co/auth/v1/token?grant_type=password

Headers:
  apikey: eyJhbGciOiJIUzI1NiIs...8EnpfifsIXkX0OLTnEdE0eMMXwhIKJHQYLR_Bof0M60
  Content-Type: application/json

Body:
{
    "email": "user@example.com",
    "password": "password123"
}

Response (200 OK):
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600,
    "expires_at": 1772181741,
    "refresh_token": "v1.MHhk...",
    "user": {
        "id": "uuid-here",
        "email": "user@example.com",
        "user_metadata": {
            "full_name": "Ad Soyad"
        },
        "created_at": "2025-02-27T..."
    }
}

Error (400):
{
    "error": "invalid_grant",
    "error_description": "Invalid login credentials"
}
```

#### 2.2.2 Register (Sign Up)

```
POST https://xxgvnqnykkbkhjdnizge.supabase.co/auth/v1/signup

Headers:
  apikey: <SUPABASE_ANON_KEY>
  Content-Type: application/json

Body:
{
    "email": "newuser@example.com",
    "password": "password123",
    "data": {
        "full_name": "Ad Soyad"
    }
}

Response (200 OK):
{
    "id": "uuid-here",
    "email": "newuser@example.com",
    "confirmation_sent_at": "2025-02-27T...",
    "user_metadata": {
        "full_name": "Ad Soyad"
    }
}
```

> **Not:** Email onayı aktif ise kullanıcı email'deki linke tıklamadan login yapamaz.

#### 2.2.3 Token Refresh

```
POST https://xxgvnqnykkbkhjdnizge.supabase.co/auth/v1/token?grant_type=refresh_token

Headers:
  apikey: <SUPABASE_ANON_KEY>
  Content-Type: application/json

Body:
{
    "refresh_token": "v1.MHhk..."
}

Response (200 OK):
{
    "access_token": "yeni-access-token...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "yeni-refresh-token...",
    "user": { ... }
}
```

#### 2.2.4 Get User (Token ile)

```
GET https://xxgvnqnykkbkhjdnizge.supabase.co/auth/v1/user

Headers:
  apikey: <SUPABASE_ANON_KEY>
  Authorization: Bearer <access_token>
```

### 2.3 iOS AuthManager Konfigürasyonu

```swift
// SupabaseConfig.swift
enum SupabaseConfig {
    static let url = "https://xxgvnqnykkbkhjdnizge.supabase.co"
    static let anonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4Z3ZucW55a2tia2hqZG5pemdlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIxNzgxNDEsImV4cCI6MjA4Nzc1NDE0MX0.8EnpfifsIXkX0OLTnEdE0eMMXwhIKJHQYLR_Bof0M60"
    static let authURL = "\(url)/auth/v1"
}
```

### 2.4 Token Lifecycle (iOS)

```
1. Login → access_token + refresh_token döner
2. access_token → Keychain'de sakla (KeychainAccess)
3. refresh_token → Keychain'de sakla
4. Her API isteğinde → Authorization: Bearer <access_token> ekle
5. 401 yanıt → refresh_token ile yeni token al
6. Refresh başarısız → Keychain temizle → Login ekranına yönlendir
7. access_token expiry: 3600 saniye (1 saat) — proaktif refresh önerilir
```

---

## 3. BACKEND API AUTH MEKANİZMASI

### 3.1 Nasıl Çalışıyor

Backend (`backend/app/core/auth.py`) Supabase JWT'yi şu şekilde doğruluyor:

```python
# 1. Authorization header'dan token al
auth_header = request.headers.get("Authorization", "")
token = auth_header[7:]  # "Bearer " kısmını kaldır

# 2. JWT decode (HS256 algoritma, audience: "authenticated")
payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")

# 3. user_id = payload["sub"] (Supabase UUID)
user_id = payload.get("sub")

# 4. Kullanıcıyı DB'de bul veya ilk girişte otomatik oluştur
user = db.query(User).filter(User.id == user_id).first()
if not user:
    user = User(id=user_id, email=email, full_name=name, plan_tier="free")
```

### 3.2 iOS'tan API Çağrısı Formatı

```
GET /api/dashboard/summary HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json
```

**Kritik:** `Authorization: Bearer <supabase_access_token>` — Supabase'den alınan `access_token` doğrudan backend'e gönderilir. Backend bu token'ı kendi `SUPABASE_JWT_SECRET` ile doğrular.

### 3.3 Hata Yanıtları

| Status | Durum | iOS Aksiyonu |
|--------|-------|--------------|
| 401 | Token yok/geçersiz/expired | Refresh dene, başarısızsa logout |
| 403 | Yetki yok | Hata mesajı göster |
| 429 | Rate limit | Retry-After header'a göre bekle |
| 500 | Server hatası | Genel hata mesajı |

---

## 4. DASHBOARD ENDPOINT'LERİ — DETAYLI RESPONSE FORMAT

### 4.1 GET /api/dashboard/summary

**Kaynak:** `backend/app/api/dashboard_routes.py:21-135`

```json
{
    "sku_overview": {
        "total": 145,
        "limit": 1000,
        "usage_percent": 14.5,
        "by_platform": {
            "hepsiburada": 98,
            "trendyol": 47
        }
    },
    "alerts": {
        "today_count": 3,
        "threshold_violations": [
            {
                "product_id": "uuid-1",
                "product_name": "Ürün Adı",
                "sku": "HBV00001234",
                "platform": "hepsiburada",
                "current_price": 139.90,
                "threshold_price": 149.90,
                "seller": "Satıcı Adı"
            }
        ]
    },
    "plan": {
        "tier": "pro",
        "sku_limit": 1000
    },
    "last_scan": {
        "at": "2026-03-01T10:30:00",
        "next": "2026-03-01T16:30:00"
    },
    "recent_searches": [
        {
            "keyword": "laptop",
            "platform": "hepsiburada",
            "products": 45,
            "date": "2026-02-28T14:20:00"
        }
    ]
}
```

### 4.2 GET /api/dashboard/price-movers

**Kaynak:** `backend/app/api/dashboard_routes.py:138-191`

```json
{
    "price_drops": [
        {
            "product_id": "uuid-1",
            "product_name": "Ürün Adı",
            "sku": "HBV0001",
            "platform": "hepsiburada",
            "old_price": 199.90,
            "new_price": 179.90,
            "change_percent": -10.0,
            "direction": "down"
        }
    ],
    "price_increases": [
        {
            "product_id": "uuid-2",
            "product_name": "Başka Ürün",
            "sku": "HBV0002",
            "platform": "trendyol",
            "old_price": 99.90,
            "new_price": 119.90,
            "change_percent": 20.0,
            "direction": "up"
        }
    ]
}
```

### 4.3 GET /api/dashboard/profitability-overview

**Kaynak:** `backend/app/api/dashboard_routes.py:194-253`

```json
{
    "total_products_with_cost": 45,
    "profitable_count": 38,
    "losing_count": 7,
    "top_profitable": [
        {
            "product_id": "uuid-1",
            "product_name": "Ürün Adı",
            "sku": "HBV0001",
            "sale_price": 299.90,
            "net_profit": 85.50,
            "margin_percent": 28.5,
            "profitable": true
        }
    ],
    "top_losing": [
        {
            "product_id": "uuid-3",
            "product_name": "Zararlı Ürün",
            "sku": "HBV0003",
            "sale_price": 49.90,
            "net_profit": -12.30,
            "margin_percent": -24.6,
            "profitable": false
        }
    ]
}
```

---

## 5. PRICE MONITOR ENDPOINT'LERİ — DETAYLI BİLGİ

### 5.1 GET /api/price-monitor/products

**Kaynak:** `backend/app/api/price_monitor_routes.py`

**Query Parameters:**

| Param | Tip | Default | Açıklama |
|-------|-----|---------|----------|
| `platform` | string | `"hepsiburada"` | `hepsiburada` veya `trendyol` |
| `limit` | int | `100` | Max 500 |
| `offset` | int | `0` | Pagination offset |
| `active_only` | bool | `true` | Sadece aktif ürünler |
| `brand` | string | `null` | Marka filtresi |
| `price_alert_only` | bool | `false` | Sadece fiyat alarmı olanlar |
| `campaign_alert_only` | bool | `false` | Sadece kampanya alarmı olanlar |
| `search` | string | `null` | Ad/SKU/barkod araması |

**Response:**

```json
{
    "products": [
        {
            "id": "uuid-1",
            "platform": "hepsiburada",
            "sku": "HBV00001234567",
            "barcode": "8680000123456",
            "product_url": "https://www.hepsiburada.com/...-p-HBV00001234567",
            "product_name": "Ürün Adı Burada",
            "brand": "Marka",
            "seller_stock_code": "STK001",
            "image_url": "https://productimages.hepsiburada.net/...",
            "threshold_price": 149.90,
            "alert_campaign_price": 129.90,
            "unit_cost": 80.00,
            "shipping_cost": 5.00,
            "is_active": true,
            "last_fetched_at": "2026-03-01T10:30:00",
            "seller_count": 5,
            "has_price_alert": true,
            "price_alert_count": 2,
            "has_campaign_alert": false,
            "campaign_alert_count": 0,
            "latest_seller": {
                "merchant_name": "En İyi Satıcı",
                "price": 139.90,
                "original_price": 159.90,
                "campaign_price": null,
                "buybox_order": 1
            }
        }
    ],
    "total": 145,
    "limit": 100,
    "offset": 0,
    "active_count": 140,
    "inactive_count": 5
}
```

### 5.2 POST /api/price-monitor/products/import (CSV/XLSX)

**Kaynak:** `backend/app/api/price_monitor_routes.py:142-318`

**Request:** Multipart form data

```
POST /api/price-monitor/products/import?platform=hepsiburada
Content-Type: multipart/form-data

file: <csv_or_xlsx_file>
```

**Desteklenen CSV/XLSX kolonları:**

| Kolon Adayları | Alan |
|----------------|------|
| `sku`, `ürün kodu`, `urun kodu`, `product_code` | SKU |
| `barcode`, `barkod` | Barkod |
| `name`, `ürün adı`, `urun adi`, `product_name` | Ad |
| `brand`, `marka` | Marka |
| `threshold`, `eşik`, `esik`, `threshold_price` | Eşik fiyat |
| `cost`, `maliyet`, `unit_cost`, `birim maliyet` | Birim maliyet |
| `shipping`, `kargo`, `shipping_cost` | Kargo maliyeti |
| `url`, `link`, `product_url` | Ürün URL |
| `seller_stock`, `stok kodu`, `stok_kodu` | Satıcı stok kodu |

**Response (mevcut):**

```json
{
    "success": true,
    "added": 42,
    "updated": 3,
    "skipped": 0,
    "errors": [
        {"row": 5, "error": "SKU bulunamadı"},
        {"row": 12, "error": "SKU bulunamadı"}
    ],
    "total_rows": 47
}
```

> **Durum:** Response zaten `added`, `updated`, `skipped` ve `errors` alanlarını içeriyor. Spec'teki `imported_count` + `failed_items` isteği mevcut yapıyla karşılanıyor. iOS'ta `added + updated` → imported, `errors` → failed_items olarak map edilebilir.

### 5.3 POST /api/price-monitor/fetch

**Request:**

```json
{
    "platform": "hepsiburada",
    "fetch_type": "active",
    "product_ids": null
}
```

`fetch_type` seçenekleri: `"active"` | `"last_inactive"` | `"inactive"`

**Response:**

```json
{
    "task_id": "uuid-task",
    "status": "running",
    "total_products": 145,
    "completed_products": 0,
    "failed_products": 0,
    "created_at": "2026-03-01T11:00:00"
}
```

### 5.4 GET /api/price-monitor/fetch/{task_id} (Polling)

**Polling interval:** Web'de 2 saniye. iOS'te de 2 saniye önerilir.

```json
{
    "id": "uuid-task",
    "status": "running",
    "total_products": 145,
    "completed_products": 67,
    "failed_products": 2,
    "created_at": "2026-03-01T11:00:00",
    "completed_at": null
}
```

**Status değerleri:** `pending` | `running` | `completed` | `failed` | `stopped`

Polling'i durdur: `status` in `["completed", "failed", "stopped"]`

### 5.5 GET /api/price-monitor/products/{id}/history

**Query Parameters:** `start_date`, `end_date` (ISO format, opsiyonel)

**Response:**

```json
{
    "product_id": "uuid-1",
    "history": [
        {
            "date": "2026-02-25",
            "price": 159.90,
            "original_price": 179.90,
            "campaign_price": null,
            "seller_count": 5
        },
        {
            "date": "2026-02-26",
            "price": 149.90,
            "original_price": 179.90,
            "campaign_price": 139.90,
            "seller_count": 5
        }
    ]
}
```

---

## 6. SELLERS ENDPOINT'LERİ — DETAYLI BİLGİ

### 6.1 GET /api/sellers

**Kaynak:** `backend/app/api/seller_routes.py:200-330`

**Query Parameters:**

| Param | Tip | Default |
|-------|-----|---------|
| `platform` | string | `"hepsiburada"` |
| `limit` | int | `100` (max 1000) |
| `offset` | int | `0` |

**Response:**

```json
{
    "sellers": [
        {
            "merchant_id": "abc123",
            "merchant_name": "Satıcı Adı",
            "merchant_logo": "https://images.hepsiburada.net/merchants/abc123.png",
            "merchant_url_postfix": "/magaza/satici-adi",
            "merchant_rating": 9.2,
            "product_count": 45,
            "price_alert_count": 3,
            "campaign_alert_count": 2
        }
    ],
    "total": 28,
    "limit": 100,
    "offset": 0
}
```

### 6.2 Satıcı Logo URL Durumu

**Kaynak kodu analizi:**

Hepsiburada Listings API'sinden logo çekiliyor (`backend/app/services/price_monitor_service.py:396`):

```python
'merchant_logo': listing.get('logo'),
```

Bu değer `seller_snapshots` tablosundaki `merchant_logo` kolonuna kaydediliyor (`backend/app/db/models.py:235`).

**Durum:** Logo URL'leri HB için genelde dolu geliyor (Listings API `logo` alanından). Trendyol için SSR parse'da logo bilgisi çekilmiyor, dolayısıyla genelde `null`.

**iOS için öneri:**
- `merchant_logo` varsa → `AsyncImage` ile göster
- `null` ise → SF Symbol placeholder: `person.crop.circle.fill` (gri)
- Alternatif: Satıcı adının ilk 2 harfi ile renkli avatar oluştur

### 6.3 GET /api/sellers/{merchant_id}/products

**Query Parameters:**

| Param | Tip | Default |
|-------|-----|---------|
| `platform` | string | `"hepsiburada"` |
| `price_alert_only` | bool | `false` |
| `campaign_alert_only` | bool | `false` |
| `limit` | int | `100` |
| `offset` | int | `0` |

**Response:**

```json
{
    "merchant_id": "abc123",
    "merchant_name": "Satıcı Adı",
    "products": [
        {
            "product_id": "uuid-1",
            "product_name": "Ürün Adı",
            "sku": "HBV0001",
            "barcode": "8680001",
            "brand": "Marka",
            "threshold_price": 149.90,
            "alert_campaign_price": 129.90,
            "seller_price": 139.90,
            "original_price": 159.90,
            "campaign_price": null,
            "buybox_order": 1,
            "has_price_alert": true,
            "has_campaign_alert": false,
            "last_fetched_at": "2026-03-01T10:30:00"
        }
    ],
    "total": 45
}
```

### 6.4 GET /api/sellers/{merchant_id}/export

CSV dosyası döner (UTF-8 BOM ile Excel uyumlu).

```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="seller_abc123_products.csv"
```

---

## 7. BACKEND'DE BULUNMAYAN AMA İHTİYAÇ DUYULAN ENDPOINT'LER

Aşağıdaki endpoint'ler mevcut backend'de **henüz yok** ve iOS uygulaması için **eklenmesi gerekecek:**

### 7.1 Push Notification Device Registration (YENİ GEREK)

```
POST /api/notifications/register-device
Authorization: Bearer <token>

Body:
{
    "device_token": "apns_hex_token_here",
    "platform": "ios",
    "app_version": "1.0.0",
    "os_version": "17.0"
}

Response:
{
    "success": true,
    "device_id": "uuid"
}
```

```
DELETE /api/notifications/unregister-device
Authorization: Bearer <token>

Body:
{
    "device_token": "apns_hex_token_here"
}
```

**Gereklilik:** Backend'in price alert/campaign alert tetiklediğinde APNs üzerinden push göndermesi için.

### 7.2 Notification Preferences (YENİ GEREK)

Web frontend'deki Settings > Bildirimler tab'ı şu an **backend'e kaydetmiyor** — sadece static UI. iOS için bu API zorunlu:

```
GET /api/notifications/preferences
Authorization: Bearer <token>

Response:
{
    "push_enabled": true,
    "price_alerts": true,
    "campaign_alerts": true,
    "daily_summary": false,
    "weekly_report": true
}
```

```
PUT /api/notifications/preferences
Authorization: Bearer <token>

Body:
{
    "push_enabled": true,
    "price_alerts": true,
    "campaign_alerts": true,
    "daily_summary": false,
    "weekly_report": true
}
```

### 7.3 Onboarding Status (YENİ GEREK)

Web'de `localStorage.setItem('mp_onboarding_done', '1')` ile tutuluyor. Cihazlar arası senkronize olmuyor.

```
GET /api/user/onboarding-status
Authorization: Bearer <token>

Response:
{
    "completed": false,
    "completed_at": null
}
```

```
PUT /api/user/onboarding-status
Authorization: Bearer <token>

Body:
{
    "completed": true
}
```

### 7.4 App Version Check (ÖNERİ)

```
GET /api/mobile/version-check?platform=ios&version=1.0.0

Response:
{
    "force_update": false,
    "recommended_update": true,
    "latest_version": "1.1.0",
    "update_url": "https://apps.apple.com/app/marketpulse/id..."
}
```

---

## 8. MEVCUT ENV DEĞİŞKENLERİ ÖZETİ

Backend'in tam çalışması için gereken env değişkenleri (`backend/app/core/config.py`):

| Değişken | iOS İlgisi | Açıklama |
|----------|------------|----------|
| `DATABASE_URL` | Hayır | PostgreSQL (Neon) |
| `SUPABASE_URL` | **Evet** | iOS auth için |
| `SUPABASE_ANON_KEY` | **Evet** | iOS auth için |
| `SUPABASE_JWT_SECRET` | Hayır | Backend JWT doğrulama |
| `SUPABASE_SERVICE_ROLE_KEY` | Hayır | Backend admin ops |
| `INTERNAL_API_KEY` | Hayır | Backend internal auth |
| `SCRAPER_API_KEY` | Hayır | Scraping servisi |
| `OPENAI_API_KEY` | Hayır | AI chat servisi |
| `REDIS_URL` | Hayır | Celery broker |
| `STRIPE_SECRET_KEY` | Hayır | Ödeme backend |
| `STRIPE_PUBLISHABLE_KEY` | Hayır | iOS'ta gerekmez (Stripe Checkout web redirect) |
| `RESEND_API_KEY` | Hayır | Email servisi |
| `CORS_ALLOWED_ORIGINS` | Hayır | iOS CORS'a tabi değil |

**iOS uygulamasında sadece 2 credential saklanacak:**
1. `SUPABASE_URL` — hardcoded config
2. `SUPABASE_ANON_KEY` — hardcoded config
3. `access_token` — Keychain (runtime, kullanıcıya özel)
4. `refresh_token` — Keychain (runtime, kullanıcıya özel)

---

## 9. BACKEND ÇALIŞTIRMA (GELİŞTİRME)

iOS geliştirme sırasında backend'i local'de çalıştırmak için:

```bash
cd /Users/projectx/Desktop/marketpulse/backend
python run.py
# veya
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Health check:** `curl http://localhost:8000/health`

```json
{"status": "healthy", "db_initialized": true}
```

**Deep health check:** `curl http://localhost:8000/health/deep`

```json
{
    "status": "healthy",
    "db_initialized": true,
    "scraper_api_configured": true,
    "price_monitor_executor": "local",
    "database_reachable": true,
    "queue_reachable": true
}
```

---

## 10. ÖZET CHECKLIST

### iOS Projesine Eklenecek Config

- [ ] `SupabaseConfig.swift` — URL + Anon Key
- [ ] `Configuration.swift` — API Base URL (debug/release)
- [ ] `Info.plist` — ATS exception (localhost, debug only)
- [ ] `KeychainService.swift` — access_token + refresh_token storage

### Backend'e Eklenecek Endpoint'ler (iOS Öncesi)

- [ ] `POST /api/notifications/register-device`
- [ ] `DELETE /api/notifications/unregister-device`
- [ ] `GET/PUT /api/notifications/preferences`
- [ ] `GET/PUT /api/user/onboarding-status`
- [ ] `GET /api/mobile/version-check` (opsiyonel)

### Backend'de Değişiklik Gerektirmeyen (Hazır)

- [x] Dashboard 3 endpoint
- [x] Price Monitor tüm CRUD + fetch + polling
- [x] Price Monitor CSV/XLSX import (response zaten detaylı)
- [x] Sellers liste + detay + export
- [x] Category Explorer tüm endpoint'ler
- [x] Billing (Stripe checkout + portal)
- [x] AI Chat (conversation-based)
- [x] Scheduler (CRUD)
- [x] Reports (weekly + price changes)
- [x] Auth (Supabase JWT doğrulama)
- [x] CORS (iOS için değişiklik gerekmez)
