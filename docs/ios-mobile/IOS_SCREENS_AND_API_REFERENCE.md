# MarketPulse iOS — Ekran Şemaları & API Referansı

> Bu doküman, MarketPulse web uygulamasındaki TÜM ekranları, her ekranın çağırdığı API endpoint'lerini,
> request/response yapılarını ve tüm filtreleme özelliklerini içerir.
> iOS (Swift/SwiftUI) geliştirme sırasında LLM Agent'ın kullanacağı TEK KAYNAK belgedir.

**Kaynak:** Web frontend (`frontend/src/`) + Backend API (`backend/app/api/`)
**Son Güncelleme:** 2026-03-02

---

## TABLE OF CONTENTS

1. [Auth — Login & Register](#1-auth--login--register)
2. [Onboarding](#2-onboarding)
3. [Dashboard (Tab 1)](#3-dashboard-tab-1)
4. [Price Monitor (Tab 2)](#4-price-monitor-tab-2)
5. [Price Monitor — Ürün Detay](#5-price-monitor--ürün-detay)
6. [Price Monitor — Fetch Progress](#6-price-monitor--fetch-progress)
7. [Price Monitor — Import](#7-price-monitor--import)
8. [Sellers (Tab 3)](#8-sellers-tab-3)
9. [Seller Detail](#9-seller-detail)
10. [Category Explorer (Tab 4)](#10-category-explorer-tab-4)
11. [Category Explorer — Kategori Tarama](#11-category-explorer--kategori-tarama)
12. [Category Explorer — Ürün Detay](#12-category-explorer--ürün-detay)
13. [Settings (Tab 5)](#13-settings-tab-5)
14. [AI Chat (Floating)](#14-ai-chat-floating)
15. [Mobilde Olmayan Ekranlar (Web-only Referans)](#15-mobilde-olmayan-ekranlar-web-only-referans)
16. [Ortak TypeScript/Swift Model Eşlemesi](#16-ortak-typescriptswift-model-eşlemesi)
17. [Tüm Endpoint Özet Tablosu](#17-tüm-endpoint-özet-tablosu)

---

## 1. Auth — Login & Register

### 1.1 LoginView

**Web karşılığı:** `pages/Login.tsx`

```
┌─────────────────────────────────┐
│                                 │
│        [MarketPulse Logo]       │
│                                 │
│   ┌───────────────────────────┐ │
│   │ 📧 Email                  │ │
│   └───────────────────────────┘ │
│   ┌───────────────────────────┐ │
│   │ 🔒 Şifre             [👁] │ │
│   └───────────────────────────┘ │
│                                 │
│   ┌───────────────────────────┐ │
│   │      Giriş Yap            │ │  ← Primary, full-width
│   └───────────────────────────┘ │
│                                 │
│   Hesabınız yok mu? [Kayıt Ol] │
│                                 │
└─────────────────────────────────┘
```

**API Çağrısı:**

```
POST https://{SUPABASE_URL}/auth/v1/token?grant_type=password

Headers:
  apikey: {SUPABASE_ANON_KEY}
  Content-Type: application/json

Request Body:
{
    "email": "user@example.com",
    "password": "sifre123"
}

Response 200:
{
    "access_token": "eyJhbGci...",
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

Response 400 (hata):
{
    "error": "invalid_grant",
    "error_description": "Invalid login credentials"
}
```

**Validasyon:**
- Email: format kontrolü (iOS `TextField` + `.keyboardType(.emailAddress)`)
- Password: min 6 karakter
- Hata: inline `Text` kırmızı renk

**State:**
```swift
@State var email = ""
@State var password = ""
@State var error = ""
@State var isSubmitting = false
```

**iOS Davranış:**
- `isSubmitting = true` → button disabled + "Giriş yapılıyor..."
- Başarılı → token Keychain'e kaydet → onboarding kontrol → MainTabView veya OnboardingView
- Zaten giriş yapmış → otomatik redirect

---

### 1.2 RegisterView

**Web karşılığı:** `pages/Register.tsx`

```
┌─────────────────────────────────┐
│        [MarketPulse Logo]       │
│                                 │
│   ┌───────────────────────────┐ │
│   │ 👤 Ad Soyad               │ │
│   └───────────────────────────┘ │
│   ┌───────────────────────────┐ │
│   │ 📧 Email                  │ │
│   └───────────────────────────┘ │
│   ┌───────────────────────────┐ │
│   │ 🔒 Şifre             [👁] │ │
│   └───────────────────────────┘ │
│   ┌───────────────────────────┐ │
│   │ 🔒 Şifre Tekrar      [👁] │ │
│   └───────────────────────────┘ │
│                                 │
│   ┌───────────────────────────┐ │
│   │       Kayıt Ol            │ │
│   └───────────────────────────┘ │
│                                 │
│   Zaten hesabınız var mı?       │
│   [Giriş Yap]                  │
└─────────────────────────────────┘
```

**API Çağrısı:**

```
POST https://{SUPABASE_URL}/auth/v1/signup

Headers:
  apikey: {SUPABASE_ANON_KEY}
  Content-Type: application/json

Request Body:
{
    "email": "newuser@example.com",
    "password": "sifre123",
    "data": {
        "full_name": "Ad Soyad"
    }
}

Response 200:
{
    "id": "uuid-here",
    "email": "newuser@example.com",
    "confirmation_sent_at": "2025-02-27T...",
    "user_metadata": {
        "full_name": "Ad Soyad"
    }
}
```

**Client Validasyon:**
- `password.count < 6` → "Şifre en az 6 karakter olmalı"
- `password != passwordConfirm` → "Şifreler eşleşmiyor"

**Başarı Durumu:**
```
┌─────────────────────────────────┐
│                                 │
│           ✅ Tebrikler!         │
│                                 │
│   Email doğrulama linki         │
│   gönderildi.                   │
│                                 │
│   [Giriş Sayfasına Dön]        │
│                                 │
└─────────────────────────────────┘
```

**State:**
```swift
@State var fullName = ""
@State var email = ""
@State var password = ""
@State var passwordConfirm = ""
@State var error = ""
@State var isSuccess = false
@State var isSubmitting = false
```

---

### 1.3 Token Refresh

```
POST https://{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token

Headers:
  apikey: {SUPABASE_ANON_KEY}
  Content-Type: application/json

Request Body:
{
    "refresh_token": "v1.MHhk..."
}

Response 200:
{
    "access_token": "yeni-token...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "yeni-refresh...",
    "user": { ... }
}
```

---

## 2. Onboarding

**Web karşılığı:** `pages/Onboarding.tsx` (6 adım → iOS'ta 4 adım)

### Adım 1: Platform Seçimi

```
┌─────────────────────────────────┐
│  ●──○──○──○    1/4              │
│                                 │
│  Hangi pazaryerini              │
│  takip etmek istiyorsunuz?      │
│                                 │
│  ┌───────────────────────────┐  │
│  │  [HB Logo] Hepsiburada   │  │  ← seçili: mavi border
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  [TY Logo] Trendyol      │  │
│  └───────────────────────────┘  │
│                                 │
│          [ Devam → ]            │
└─────────────────────────────────┘
```

**API:** Yok (sadece local state)

### Adım 2: İlk SKU Ekleme

```
┌─────────────────────────────────┐
│  ●──●──○──○    2/4              │
│                                 │
│  İlk ürününüzün SKU'sunu       │
│  girin:                         │
│                                 │
│  ┌───────────────────────────┐  │
│  │ HBV00001ABC12             │  │  ← platform'a göre placeholder
│  └───────────────────────────┘  │
│                                 │
│  [Şimdilik Atla]   [Ekle →]    │
└─────────────────────────────────┘
```

**API Çağrısı:**

```
POST /api/price-monitor/products

Headers:
  Authorization: Bearer {access_token}
  Content-Type: application/json

Request Body:
{
    "products": [
        {
            "sku": "HBV00001ABC12"
        }
    ],
    "platform": "hepsiburada"
}

Response 200:
{
    "added": 1,
    "updated": 0,
    "errors": [],
    "total": 1,
    "platform": "hepsiburada"
}
```

### Adım 3: Eşik Fiyat Belirleme

```
┌─────────────────────────────────┐
│  ●──●──●──○    3/4              │
│                                 │
│  {Ürün Adı}                    │
│  SKU: HBV00001ABC12             │
│                                 │
│  Fiyat eşiği belirleyin:        │
│  ┌───────────────────────────┐  │
│  │ ₺ 149.90                  │  │
│  └───────────────────────────┘  │
│  Bu fiyatın altına düşerse      │
│  bildirim alırsınız.            │
│                                 │
│  [Şimdilik Atla]   [Devam →]   │
└─────────────────────────────────┘
```

**API Çağrısı:**

```
PUT /api/price-monitor/products/{product_id}

Headers:
  Authorization: Bearer {access_token}
  Content-Type: application/json

Request Body:
{
    "threshold_price": 149.90
}

Response 200:
{
    "success": true,
    "product": {
        "id": "uuid",
        "threshold_price": 149.90,
        ...
    }
}
```

### Adım 4: İlk Tarama + Tamamlandı

```
┌─────────────────────────────────┐
│  ●──●──●──●    4/4              │
│                                 │
│          ✅ Tebrikler!          │
│                                 │
│  İlk ürününüz eklendi.         │
│  Fiyat taraması başlatılıyor... │
│                                 │
│  [ProgressView spinning]        │
│                                 │
│  [Price Monitor'a Git →]        │
└─────────────────────────────────┘
```

**API Çağrısı:**

```
POST /api/price-monitor/fetch?platform=hepsiburada&fetch_type=active

Headers:
  Authorization: Bearer {access_token}

Request Body: null

Response 200:
{
    "task_id": "uuid-task",
    "platform": "hepsiburada",
    "fetch_type": "active",
    "executor": "local",
    "status": "started",
    "message": "Fiyat çekme görevi başlatıldı"
}
```

**Tamamlanma:** `UserDefaults.set(true, forKey: "onboarding_completed")`

**State:**
```swift
@State var step: OnboardingStep = .platform  // .platform, .addSku, .threshold, .done
@State var platform: Platform = .hepsiburada
@State var sku = ""
@State var threshold = ""
@State var isLoading = false
@State var error = ""
@State var addedProduct: (id: String, name: String)? = nil
```

---

## 3. Dashboard (Tab 1)

**Web karşılığı:** `pages/Dashboard.tsx`

### Ekran Şeması

```
┌──────────────────────────────────┐
│  Dashboard            [Pro] 🌙  │  ← NavigationBar
├──────────────────────────────────┤
│  ↕ Pull to Refresh              │
│                                  │
│  ┌──────────┐  ┌──────────┐    │
│  │   45/200  │  │     3    │    │  ← 2x2 stat cards
│  │   SKU     │  │   Alarm  │    │
│  │  ████░░░  │  │   bugün  │    │
│  └──────────┘  └──────────┘    │
│  ┌──────────┐  ┌──────────┐    │
│  │  2 saat   │  │    12    │    │
│  │  Son Tar. │  │  Kârlı   │    │
│  └──────────┘  └──────────┘    │
│                                  │
│  ⚠️ Eşik İhlalleri (3)         │
│  ┌────────────────────────────┐  │
│  │ Ürün A  ₺149→₺139  ↓7.3%  │  │
│  │ Ürün B  ₺89→₺79    ↓11.2% │  │
│  │ [Tümünü Gör →]             │  │
│  └────────────────────────────┘  │
│                                  │
│  📉 Fiyat Hareketleri (7 gün)  │
│  ┌────────────────────────────┐  │
│  │ Düşüşler                   │  │
│  │  Ürün X  ₺200→₺180  -10%  │  │
│  │  Ürün Y  ₺150→₺130  -13%  │  │
│  ├────────────────────────────┤  │
│  │ Artışlar                    │  │
│  │  Ürün Z  ₺100→₺120  +20%  │  │
│  └────────────────────────────┘  │
│                                  │
│  💰 Kârlılık Özeti             │
│  ┌────────────────────────────┐  │
│  │ En Kârlı                    │  │
│  │  Ürün A  %28.5  ₺85.50    │  │
│  ├────────────────────────────┤  │
│  │ En Zararlı                  │  │
│  │  Ürün B  %-24.6  -₺12.30  │  │
│  └────────────────────────────┘  │
│                                  │
│  ⚡ Hızlı İşlemler             │
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ 📊   │ │ 👥   │ │ ⚙️   │   │
│  │Price │ │Selle.│ │Ayar. │   │
│  └──────┘ └──────┘ └──────┘   │
│                                  │
└──────────────────────────────────┘
```

### API Çağrıları (3 paralel — TaskGroup)

#### API 1: GET /api/dashboard/summary

```
GET /api/dashboard/summary

Headers:
  Authorization: Bearer {access_token}

Response 200:
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

#### API 2: GET /api/dashboard/price-movers

```
GET /api/dashboard/price-movers

Headers:
  Authorization: Bearer {access_token}

Response 200:
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
            "sku": "TY123",
            "platform": "trendyol",
            "old_price": 99.90,
            "new_price": 119.90,
            "change_percent": 20.0,
            "direction": "up"
        }
    ]
}
```

#### API 3: GET /api/dashboard/profitability-overview

```
GET /api/dashboard/profitability-overview

Headers:
  Authorization: Bearer {access_token}

Response 200:
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

### Filtreler
- **Yok.** Dashboard salt görüntüleme ekranıdır.

### State
```swift
@Observable class DashboardViewModel {
    var summary: DashboardSummary?
    var priceMovers: PriceMovers?
    var profitability: ProfitabilityOverview?
    var isLoading = true
    var error: AppError?
}
```

### iOS Davranış
- Pull-to-refresh ile 3 API paralel çağrılır
- Skeleton loading (4 kart + 2 section)
- Threshold ihlali satırına tap → Price Monitor tab'ına geçiş
- Quick action kartları → ilgili tab'a geçiş

---

## 4. Price Monitor (Tab 2)

**Web karşılığı:** `pages/PriceMonitor.tsx` + `hooks/usePriceMonitor.ts`

### Ekran Şeması

```
┌──────────────────────────────────┐
│  Price Monitor      [+] [📥] [↻]│  ← Nav: Import, Export, Fetch
├──────────────────────────────────┤
│                                  │
│  [Hepsiburada] [Trendyol]       │  ← Segmented Control
│                                  │
│  🔍 Ürün, SKU, barkod ara...    │  ← SearchBar (debounce 400ms)
│                                  │
│  [Marka ▾]                      │  ← Picker/Menu
│  [⚠️ Fiyat Alarmı] [🏷 Kampanya]│  ← Toggle chips
│                                  │
│  Aktif: 140  |  İnaktif: 5      │  ← Summary bar
│                                  │
│  ┌────────────────────────────┐  │
│  │ [📦img] Ürün Adı Burada   │  │
│  │ SKU: HBV00012 | Marka X   │  │
│  │ ₺149.90   ⚠️₺139(eşik)   │  │
│  │ 5 satıcı | 2 saat önce    │  │
│  │                   [↻] [🗑] │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ [📦img] Başka Ürün         │  │
│  │ SKU: HBV00034 | Marka Y   │  │
│  │ ₺299.90   🏷₺269(kamp.)   │  │
│  │ 3 satıcı | 5 saat önce    │  │
│  └────────────────────────────┘  │
│  ...                             │
│                                  │
│  ──── Sayfa 1/3  [◀] [▶] ────  │
│                                  │
└──────────────────────────────────┘
```

### API Çağrısı: Ürün Listesi

```
GET /api/price-monitor/products?platform=hepsiburada&limit=100&offset=0

Headers:
  Authorization: Bearer {access_token}

Tüm Query Parameters:
  platform: string        ← "hepsiburada" | "trendyol"
  limit: int              ← default 100, max 500
  offset: int             ← default 0 (pagination)
  active_only: bool       ← default false
  brand: string?          ← filtre: marka adı
  price_alert_only: bool  ← default false
  campaign_alert_only: bool ← default false
  search: string?         ← ürün adı / SKU / barkod araması

Response 200:
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
            "is_active": true,
            "last_fetched_at": "2026-03-01T10:30:00",
            "seller_count": 5,
            "has_price_alert": true,
            "price_alert_count": 2,
            "has_campaign_alert": false,
            "campaign_alert_count": 0
        }
    ],
    "total": 145,
    "active_count": 140,
    "inactive_count": 5,
    "limit": 100,
    "offset": 0
}
```

### API Çağrısı: Marka Listesi

```
GET /api/price-monitor/brands?platform=hepsiburada

Response 200:
{
    "brands": ["Apple", "Samsung", "Xiaomi", "Philips", ...]
}
```

### API Çağrısı: Tek Ürün Refresh

```
POST /api/price-monitor/fetch-single/{product_id}

Response 200:
{
    "success": true,
    "message": "Fiyat güncellendi",
    "platform": "hepsiburada"
}
```

### API Çağrısı: Ürün Sil

```
DELETE /api/price-monitor/products/{product_id}

Response 200:
{
    "success": true,
    "message": "Ürün silindi"
}
```

### API Çağrısı: Toplu Sil (Tümü)

```
DELETE /api/price-monitor/products/bulk/all?platform=hepsiburada

Response 200:
{
    "success": true,
    "deleted_count": 140,
    "message": "140 ürün silindi"
}
```

### API Çağrısı: Toplu Sil (İnaktifler)

```
DELETE /api/price-monitor/products/bulk/inactive?platform=hepsiburada

Response 200:
{
    "success": true,
    "deleted_count": 5,
    "message": "5 inaktif ürün silindi"
}
```

### API Çağrısı: Export

```
GET /api/price-monitor/export?platform=hepsiburada&active_filter=all

active_filter: "all" | "active" | "inactive"

Response: JSON dosyası (blob download)
Content-Type: application/json
Content-Disposition: attachment; filename="price_monitor_hepsiburada_20260301.json"
```

### API Çağrısı: Last Inactive SKUs

```
GET /api/price-monitor/last-inactive?platform=hepsiburada

Response 200:
{
    "skus": ["HBV001", "HBV002"],
    "count": 2,
    "products": [
        {
            "id": "uuid",
            "sku": "HBV001",
            "product_name": "Ürün Adı",
            "brand": "Marka",
            "is_active": false
        }
    ],
    "task_id": "uuid-task",
    "completed_at": "2026-03-01T10:00:00"
}
```

### Tüm Filtreler (iOS)

| Filtre | UI Bileşeni | API Parametresi | Davranış |
|--------|-------------|-----------------|----------|
| Platform | `Picker` (Segmented) | `platform` | Değişimde liste sıfırlanır |
| Arama | `TextField` (debounce 400ms) | `search` | Ad/SKU/barkod'da arar |
| Marka | `Menu`/`Picker` | `brand` | Dinamik liste (brands endpoint) |
| Fiyat Alarmı | Toggle chip | `price_alert_only=true` | Sadece eşik ihlali olanlar |
| Kampanya Alarmı | Toggle chip | `campaign_alert_only=true` | Sadece kampanya alarmı olanlar |

### Pagination
- `PAGE_SIZE = 100` sabit
- `offset` state ile yönetilir
- Platform/filtre değişiminde `offset = 0`'a sıfırlanır
- "Önceki" / "Sonraki" butonları

### State
```swift
@Observable class PriceMonitorViewModel {
    var products: [MonitoredProduct] = []
    var platform: Platform = .hepsiburada
    var searchText = ""           // debounced 400ms
    var brands: [String] = []
    var selectedBrand: String?
    var priceAlertOnly = false
    var campaignAlertOnly = false
    var isLoading = false
    var currentOffset = 0
    var totalCount = 0
    var activeCount = 0
    var inactiveCount = 0
    var fetchTask: FetchTask?     // aktif fetch varsa
    var isFetching = false
}
```

---

## 5. Price Monitor — Ürün Detay

**Web karşılığı:** `components/price-monitor/SellerDetailPanel.tsx` (sağ panel → iOS'ta NavigationLink push)

### Ekran Şeması

```
┌──────────────────────────────────┐
│  ← Ürün Adı                     │
├──────────────────────────────────┤
│  [Ürün Resmi — AsyncImage]      │
│                                  │
│  SKU: HBV00001234567             │
│  Barkod: 8680000123456           │
│  Marka: Apple                    │
│  Platform: Hepsiburada           │
│                                  │
│  ┌────────┐  ┌────────┐        │
│  │ ₺149   │  │ ₺139   │        │
│  │ Eşik   │  │ Kamp.  │        │
│  └────────┘  └────────┘        │
│  ┌────────┐  ┌────────┐        │
│  │   5    │  │  ⚠️ 2  │        │
│  │ Satıcı │  │ Alarm  │        │
│  └────────┘  └────────┘        │
│                                  │
│  📊 Fiyat Geçmişi              │
│  [7G] [30G] [90G]              │  ← Period picker
│  ┌────────────────────────────┐  │
│  │     📈 Swift Charts        │  │
│  │     Line + PointMark       │  │
│  └────────────────────────────┘  │
│                                  │
│  👥 Satıcılar (5)              │
│  ┌────────────────────────────┐  │
│  │ 🏆 1. Satıcı A             │  │
│  │   ₺149.90 | ⭐4.8 | 📦HBF │  │
│  │   🚚 Ücretsiz | ⚡ Hızlı   │  │
│  │   🏷 Sepette %5 indirim    │  │
│  ├────────────────────────────┤  │
│  │ 2. Satıcı B                 │  │
│  │   ₺155.00 | ⭐4.5          │  │
│  │   🚚 Ücretsiz              │  │
│  ├────────────────────────────┤  │
│  │ 3. Satıcı C  ⚠️            │  │
│  │   ₺135.00 | ⭐4.2          │  │  ← eşik altı = kırmızı
│  │   🏷 Kampanya aktif        │  │
│  └────────────────────────────┘  │
│                                  │
│  [🌐 Pazaryerinde Görüntüle →] │  ← SFSafariViewController
│                                  │
└──────────────────────────────────┘
```

### API Çağrısı: Ürün + Satıcılar

```
GET /api/price-monitor/products/{product_id}

Response 200:
{
    "product": {
        "id": "uuid-1",
        "platform": "hepsiburada",
        "sku": "HBV00001234567",
        "barcode": "8680000123456",
        "product_url": "https://...",
        "product_name": "Ürün Adı",
        "brand": "Apple",
        "seller_stock_code": "STK001",
        "threshold_price": 149.90,
        "alert_campaign_price": 129.90,
        "image_url": "https://...",
        "is_active": true,
        "last_fetched_at": "2026-03-01T10:30:00",
        "seller_count": 5,
        "has_price_alert": true,
        "price_alert_count": 2,
        "has_campaign_alert": true,
        "campaign_alert_count": 1
    },
    "sellers": [
        {
            "merchant_id": "abc123",
            "merchant_name": "Satıcı A",
            "merchant_logo": "https://images.hepsiburada.net/...",
            "merchant_url_postfix": "/magaza/satici-a",
            "merchant_url": "https://www.hepsiburada.com/magaza/satici-a",
            "merchant_rating": 9.5,
            "merchant_rating_count": 12450,
            "merchant_city": "İstanbul",
            "price": 149.90,
            "list_price": 149.90,
            "original_price": 179.90,
            "minimum_price": 139.90,
            "discount_rate": 16.7,
            "stock_quantity": 50,
            "buybox_order": 1,
            "free_shipping": true,
            "fast_shipping": true,
            "is_fulfilled_by_hb": true,
            "campaigns": ["Sepette %5 indirim", "3 al 2 öde"],
            "campaign_price": 142.40,
            "snapshot_date": "2026-03-01T10:30:00",
            "price_alert": false,
            "campaign_alert": true
        }
    ]
}
```

### API Çağrısı: Fiyat Geçmişi (Chart)

```
GET /api/price-monitor/products/{product_id}/price-history?days=30

Query Parameters:
  days: int           ← 7, 30, 90 (picker ile seçilir)
  merchant_id: string? ← opsiyonel, belirli satıcı için

Response 200:
{
    "product_id": "uuid-1",
    "product_name": "Ürün Adı",
    "sku": "HBV0001",
    "platform": "hepsiburada",
    "days": 30,
    "total_snapshots": 45,
    "merchants": [
        {
            "merchant_id": "abc123",
            "merchant_name": "Satıcı A",
            "data_points": [
                {
                    "date": "2026-02-01T00:00:00",
                    "price": 159.90,
                    "original_price": 179.90,
                    "campaign_price": null,
                    "buybox_order": 1,
                    "stock_quantity": 50
                },
                {
                    "date": "2026-02-15T00:00:00",
                    "price": 149.90,
                    "original_price": 179.90,
                    "campaign_price": 142.40,
                    "buybox_order": 1,
                    "stock_quantity": 45
                }
            ],
            "min_price": 139.90,
            "max_price": 165.00,
            "avg_price": 152.30,
            "current_price": 149.90,
            "price_change": -10.00,
            "price_change_pct": -6.3
        }
    ],
    "buybox_timeline": [
        {
            "date": "2026-02-01T00:00:00",
            "merchant_id": "abc123",
            "merchant_name": "Satıcı A",
            "price": 159.90
        }
    ]
}
```

### Satıcı Kartı Bilgi Alanları

| Alan | Açıklama | iOS UI |
|------|----------|--------|
| `buybox_order` | 1 = kazanan | 🏆 badge (gold) |
| `price` | Satış fiyatı (kampanyalı) | Ana fiyat label |
| `original_price` | Liste fiyatı | Üstü çizili label |
| `campaign_price` | Sepet kampanya fiyatı | 🏷 badge ile |
| `free_shipping` | Ücretsiz kargo | 🚚 badge |
| `fast_shipping` | Hızlı teslimat | ⚡ badge |
| `is_fulfilled_by_hb` | HB depodan | 📦 "HBF" badge |
| `campaigns` | Kampanya listesi | Her biri ayrı chip |
| `merchant_rating` | Satıcı puanı | ⭐ X.X format |
| `price_alert` | Eşik altı mı | Kırmızı satır arka planı |
| `campaign_alert` | Kampanya eşik altı mı | Turuncu badge |

---

## 6. Price Monitor — Fetch Progress

**Web karşılığı:** `components/price-monitor/FetchTaskProgress.tsx`

### Ekran Şeması (Sheet)

```
┌──────────────────────────────────┐
│  Fiyat Güncelleme          [✕]  │
│                                  │
│  ████████████░░░░  67/145        │  ← ProgressView (linear)
│                                  │
│  Platform: Hepsiburada           │
│  Tip: Aktif Ürünler              │
│  Başarılı: 65                    │
│  Başarısız: 2                    │
│                                  │
│  ┌────────────────────────────┐  │
│  │        Durdur              │  │  ← Destructive button
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

### API Çağrısı: Fetch Başlat

```
POST /api/price-monitor/fetch?platform=hepsiburada&fetch_type=active

Query Parameters:
  platform: string         ← "hepsiburada" | "trendyol"
  fetch_type: string       ← "active" | "last_inactive" | "inactive"
  product_ids: [string]?   ← opsiyonel, belirli ürünler için

Request Body: null

Response 200:
{
    "task_id": "uuid-task",
    "platform": "hepsiburada",
    "fetch_type": "active",
    "executor": "local",
    "status": "started",
    "message": "Fiyat çekme görevi başlatıldı"
}
```

### API Çağrısı: Fetch Durumu (Polling — her 2 saniye)

```
GET /api/price-monitor/fetch/{task_id}

Response 200:
{
    "id": "uuid-task",
    "status": "running",
    "total_products": 145,
    "completed_products": 67,
    "failed_products": 2,
    "fetch_type": "active",
    "executor": "local",
    "last_inactive_count": 0,
    "created_at": "2026-03-01T11:00:00",
    "completed_at": null
}

status değerleri: "pending" | "running" | "completed" | "failed" | "stopped"
Polling durma koşulu: status ∈ ["completed", "failed", "stopped"]
```

### API Çağrısı: Fetch Durdur

```
POST /api/price-monitor/fetch/{task_id}/stop

Response 200:
{
    "success": true,
    "message": "Görev durduruldu"
}
```

### iOS Polling
```swift
// Timer.publish(every: 2.0) ile polling
// status terminal ise → timer cancel + ürün listesini refresh
```

---

## 7. Price Monitor — Import

**Web karşılığı:** `components/price-monitor/ImportModal.tsx`

### Ekran Şeması (Sheet)

```
┌──────────────────────────────────┐
│  Ürün İçe Aktar            [✕]  │
│                                  │
│  Platform: [HB ▾]               │  ← Picker
│                                  │
│  JSON yapıştırın:                │
│  ┌────────────────────────────┐  │
│  │ [{"sku":"HBV..."},         │  │  ← TextEditor
│  │  {"sku":"HBV..."}]         │  │
│  └────────────────────────────┘  │
│                                  │
│  ── veya ──                      │
│                                  │
│  [📄 CSV/Excel Dosyadan Yükle]  │  ← fileImporter
│                                  │
│  ┌────────────────────────────┐  │
│  │       İçe Aktar            │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

### API Çağrısı: JSON Import

```
POST /api/price-monitor/products

Request Body:
{
    "products": [
        {
            "sku": "HBV00001234567",
            "productName": "Ürün Adı",
            "barcode": "8680001234",
            "brand": "Apple",
            "price": 149.90,
            "campaignPrice": 129.90,
            "sellerStockCode": "STK001"
        }
    ],
    "platform": "hepsiburada"
}

Response 200:
{
    "added": 42,
    "updated": 3,
    "errors": [
        {"sku": "INVALID", "error": "Geçersiz SKU formatı"}
    ],
    "total": 45,
    "platform": "hepsiburada"
}
```

### API Çağrısı: CSV/Excel Import

```
POST /api/price-monitor/products/import?platform=hepsiburada

Content-Type: multipart/form-data
Body: file=<csv_or_xlsx>

Desteklenen Kolon Adları:
  SKU: "sku", "ürün kodu", "urun kodu", "product_code"
  Barkod: "barcode", "barkod"
  Ad: "name", "ürün adı", "product_name"
  Marka: "brand", "marka"
  Eşik: "threshold", "eşik", "threshold_price"
  Maliyet: "cost", "maliyet", "unit_cost"
  Kargo: "shipping", "kargo", "shipping_cost"
  URL: "url", "link", "product_url"
  Stok Kodu: "seller_stock", "stok kodu"

Response 200:
{
    "success": true,
    "added": 42,
    "updated": 3,
    "skipped": 0,
    "errors": [
        {"row": 5, "error": "SKU bulunamadı"}
    ],
    "total_rows": 47
}
```

---

## 8. Sellers (Tab 3)

**Web karşılığı:** `pages/Sellers.tsx`

### Ekran Şeması

```
┌──────────────────────────────────┐
│  Satıcılar              [CSV]   │
├──────────────────────────────────┤
│                                  │
│  [Hepsiburada] [Trendyol]       │  ← Segmented Control
│                                  │
│  🔍 Satıcı ara...               │  ← Client-side filtre
│                                  │
│  ┌────────────────────────────┐  │
│  │ [🖼] Satıcı Adı A          │  │
│  │ ⭐ 9.2 | 45 ürün           │  │
│  │ ⚠️ 3 fiyat | 🏷 2 kampanya │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ [🖼] Satıcı Adı B          │  │  ← Kırmızı border = price alert
│  │ ⭐ 8.7 | 23 ürün           │  │
│  │ ⚠️ 5 fiyat | 🏷 0 kampanya │  │
│  └────────────────────────────┘  │
│  ...                             │
│                                  │
└──────────────────────────────────┘
```

### API Çağrısı: Satıcı Listesi

```
GET /api/sellers?platform=hepsiburada&limit=200&offset=0

Query Parameters:
  platform: string    ← "hepsiburada" | "trendyol"
  limit: int          ← default 200, max 1000
  offset: int         ← default 0

Response 200:
{
    "sellers": [
        {
            "merchant_id": "abc123",
            "merchant_name": "Satıcı Adı",
            "merchant_logo": "https://images.hepsiburada.net/...",
            "merchant_url_postfix": "/magaza/satici-adi",
            "merchant_rating": 9.2,
            "product_count": 45,
            "price_alert_count": 3,
            "campaign_alert_count": 2
        }
    ],
    "total": 28,
    "limit": 200,
    "offset": 0
}
```

### Filtreler

| Filtre | UI Bileşeni | Uygulama | Davranış |
|--------|-------------|----------|----------|
| Platform | Segmented Control | API `platform` param | Liste yeniden yüklenir |
| Satıcı adı arama | TextField | **Client-side** | `merchant_name.contains(searchTerm)` |

### API Çağrısı: Bulk CSV Export

```
GET /api/sellers/{merchant_id}/export?platform=hepsiburada&price_alert_only=true

Query Parameters:
  platform: string
  price_alert_only: bool
  campaign_alert_only: bool

Response: CSV dosyası (blob)
Content-Type: text/csv; charset=utf-8
```

**iOS:** Share sheet ile dosya paylaşımı veya Files'a kaydetme.

### iOS Davranış
- Kart arka plan rengi: alarm durumuna göre (kırmızı/turuncu gradient)
- Satıcıya tap → SellerDetailView'a NavigationLink
- Bulk export: alert sayısı >0 olan satıcılar için sıralı export (500ms ara)

---

## 9. Seller Detail

**Web karşılığı:** `pages/SellerDetail.tsx`

### Ekran Şeması

```
┌──────────────────────────────────┐
│  ← Satıcı Adı A          [CSV] │
├──────────────────────────────────┤
│  ⭐ 9.2 | 45 ürün               │
│  ⚠️ 3 fiyat | 🏷 2 kampanya     │
│                                  │
│  🔍 Ürün ara...                  │  ← Client-side filtre
│  [⚠️ Fiyat] [🏷 Kampanya]       │  ← API toggle
│                                  │
│  ┌────────────────────────────┐  │
│  │ Ürün Adı                   │  │
│  │ SKU: HBV0001 | Apple       │  │
│  │ Eşik: ₺150                 │  │
│  │ Satıcı Fiy.: ₺139 ⚠️      │  │  ← eşik altı
│  │ Fark: -₺11 (-7.3%)        │  │
│  │ Kamp. Fiy.: ₺129 🏷       │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ Başka Ürün                  │  │
│  │ SKU: HBV0002 | Samsung     │  │
│  │ Eşik: ₺300                 │  │
│  │ Satıcı Fiy.: ₺310 ✅       │  │
│  └────────────────────────────┘  │
│  ...                             │
│                                  │
└──────────────────────────────────┘
```

### API Çağrısı: Satıcı Ürünleri

```
GET /api/sellers/{merchant_id}/products?platform=hepsiburada&price_alert_only=false&campaign_alert_only=false

Query Parameters:
  platform: string
  price_alert_only: bool    ← toggle
  campaign_alert_only: bool ← toggle
  limit: int                ← default 500, max 5000
  offset: int               ← default 0

Response 200:
{
    "products": [
        {
            "product_id": "uuid-1",
            "sku": "HBV0001",
            "barcode": "8680001",
            "product_name": "Ürün Adı",
            "product_url": "https://...",
            "seller_url": "https://...",
            "brand": "Apple",
            "seller_stock_code": "STK001",
            "image_url": "https://...",
            "threshold_price": 149.90,
            "seller_price": 139.90,
            "original_price": 179.90,
            "campaign_price": 129.90,
            "alert_campaign_price": 139.00,
            "campaigns": ["Sepette %5 indirim"],
            "price_alert": true,
            "campaign_alert": true,
            "price_difference": -10.00,
            "campaign_difference": -9.10,
            "snapshot_date": "2026-03-01T10:30:00"
        }
    ],
    "total": 45,
    "merchant_name": "Satıcı Adı A",
    "price_alert_count": 3,
    "campaign_alert_count": 2,
    "limit": 500,
    "offset": 0
}
```

### Filtreler

| Filtre | UI Bileşeni | Uygulama | Davranış |
|--------|-------------|----------|----------|
| Metin arama | TextField | **Client-side** | product_name, sku, barcode, brand |
| Fiyat Alarmı | Toggle chip | **API** `price_alert_only=true` | Yeniden yükler |
| Kampanya Alarmı | Toggle chip | **API** `campaign_alert_only=true` | Yeniden yükler |

### API Çağrısı: CSV Export

```
GET /api/sellers/{merchant_id}/export?platform=hepsiburada&price_alert_only=false&campaign_alert_only=false

Response: CSV dosyası
Kolonlar: SKU; Barcode; Product Name; Brand; Stock Code; Product URL;
          Threshold Price; Seller Price; Price Difference; Price Alert;
          Campaign Threshold; Campaign Price; Campaign Difference;
          Campaign Alert; Campaigns; Snapshot Date
```

---

## 10. Category Explorer (Tab 4)

**Web karşılığı:** `pages/CategoryExplorer.tsx` + `hooks/useCategoryExplorer.ts`

### Ekran Şeması

```
┌──────────────────────────────────┐
│  Kategori Analizi        [🔍]   │
├──────────────────────────────────┤
│                                  │
│  [Ürünlerim] [Kategori Tarama]  │  ← Segmented (viewMode)
│                                  │
│  [Tümü] [HB] [TY] [Web]        │  ← Platform pills
│                                  │
│  ┌────────┐┌────────┐┌────────┐ │
│  │ 234    ││ ₺542   ││  18    │ │  ← Stat cards
│  │ Ürün   ││Ort.Fiy.││ Marka  │ │
│  └────────┘└────────┘└────────┘ │
│                                  │
│  [Filtreler ▾]                  │  ← Sheet açar
│                                  │
│  🔍 Ürün, marka, SKU ara...     │
│  [Sıralama ▾]                   │
│                                  │
│  ┌──────┐  ┌──────┐            │
│  │[🖼]  │  │[🖼]  │            │  ← 2-column grid
│  │Ürün A│  │Ürün B│            │
│  │₺149  │  │₺299  │            │
│  │⭐4.5 │  │⭐4.8 │            │
│  └──────┘  └──────┘            │
│  ┌──────┐  ┌──────┐            │
│  │ ...  │  │ ...  │            │
│  └──────┘  └──────┘            │
│                                  │
│  ── Sayfa 1/5 [◀][▶] ──        │
│                                  │
└──────────────────────────────────┘
```

### API Çağrısı: Kendi Ürünleri (viewMode = "my_products")

```
GET /api/store-products?platform=hepsiburada&page=1&page_size=50&sort_by=created_at&sort_dir=desc

Tüm Query Parameters:
  platform: string?
  page: int             ← default 1
  page_size: int        ← default 50, max 200
  sort_by: string?      ← "created_at" | "price" | "rating" | "product_name"
  sort_dir: string?     ← "asc" | "desc"
  search: string?       ← ad/marka/SKU araması
  brand: string?
  category: string?     ← kategori full_path
  min_price: float?
  max_price: float?
  min_rating: float?
  sku: string?
  barcode: string?

Response 200:
{
    "total": 234,
    "page": 1,
    "page_size": 50,
    "total_pages": 5,
    "products": [
        {
            "id": "uuid",
            "platform": "hepsiburada",
            "source_url": "https://...",
            "sku": "HBV001",
            "barcode": "8680001",
            "product_name": "Ürün Adı",
            "brand": "Apple",
            "category": "Elektronik > Telefon",
            "category_breadcrumbs": [
                {"name": "Elektronik", "url": "https://...", "position": 1},
                {"name": "Telefon", "url": "https://...", "position": 2}
            ],
            "price": 1299.00,
            "currency": "TRY",
            "availability": "InStock",
            "rating": 4.5,
            "rating_count": 1234,
            "review_count": 567,
            "image_url": "https://...",
            "images": ["https://...1", "https://...2"],
            "description": "Ürün açıklaması...",
            "seller_name": "Satıcı",
            "shipping_info": {"cost": "Ücretsiz", "currency": "TRY"},
            "return_policy": {"days": 15, "free_return": true},
            "product_specs": {"RAM": "8GB", "Depolama": "256GB"},
            "created_at": "2026-03-01T10:00:00",
            "updated_at": "2026-03-01T10:00:00"
        }
    ],
    "filtered_stats": {
        "avg_price": 542.30,
        "brand_count": 18,
        "category_count": 7
    }
}
```

### API Çağrısı: Filtre Seçenekleri

```
GET /api/store-products/filters?platform=hepsiburada

Response 200:
{
    "brands": [
        {"name": "Apple", "count": 45},
        {"name": "Samsung", "count": 32}
    ],
    "categories": [
        {"name": "Elektronik > Telefon", "count": 67},
        {"name": "Elektronik > Laptop", "count": 34}
    ],
    "platforms": [
        {"name": "hepsiburada", "count": 150},
        {"name": "trendyol", "count": 84}
    ],
    "price_range": {"min": 9.90, "max": 45999.00, "avg": 542.30}
}
```

### API Çağrısı: Kategori Ağacı

```
GET /api/store-products/category-tree?platform=hepsiburada

Response 200:
{
    "tree": [
        {
            "name": "Elektronik",
            "full_path": "Elektronik",
            "count": 120,
            "depth": 0,
            "category_url": "https://...",
            "children": [
                {
                    "name": "Telefon",
                    "full_path": "Elektronik > Telefon",
                    "count": 67,
                    "depth": 1,
                    "category_url": "https://...",
                    "children": []
                }
            ]
        }
    ]
}
```

### Tüm Filtreler (my_products modu)

| Filtre | UI Bileşeni | API Parametresi | Default |
|--------|-------------|-----------------|---------|
| Platform | Pill buttons | `platform` | Tümü (boş) |
| Metin arama | TextField | `search` | — |
| Kategori | Kategori ağacı (sheet) | `category` | — |
| Marka | Picker (dinamik) | `brand` | — |
| Min Fiyat | TextField (.decimalPad) | `min_price` | — |
| Max Fiyat | TextField (.decimalPad) | `max_price` | — |
| Min Rating | Picker (4+, 3+, 2+) | `min_rating` | — |
| Sıralama | Picker | `sort_by` + `sort_dir` | created_at desc |

### Sıralama Seçenekleri (my_products)

| Label | sort_by | sort_dir |
|-------|---------|----------|
| En Yeni | `created_at` | `desc` |
| En Eski | `created_at` | `asc` |
| Fiyat (Artan) | `price` | `asc` |
| Fiyat (Azalan) | `price` | `desc` |
| Puan (Yüksek) | `rating` | `desc` |
| İsim (A-Z) | `product_name` | `asc` |

---

## 11. Category Explorer — Kategori Tarama

**Web karşılığı:** `hooks/useCategoryExplorer.ts` (viewMode = "category_page")

### Tarama Paneli

```
┌──────────────────────────────────┐
│  [Ürünlerim] [Kategori Tarama]  │
│                                  │
│  Kategori URL:                   │
│  ┌────────────────────────────┐  │
│  │ https://hepsiburada.com/...│  │
│  └────────────────────────────┘  │
│  Sayfa Sayısı: [5 ▾]            │
│  ┌────────────────────────────┐  │
│  │     Taramayı Başlat        │  │
│  └────────────────────────────┘  │
│                                  │
│  ── Son Oturumlar ──            │
│  ├── Laptop (HB) - 120 ürün    │
│  ├── Telefon (TY) - 89 ürün    │
│  └── Kulaklık (HB) - 45 ürün   │
└──────────────────────────────────┘
```

### API Çağrısı: Kategori Sayfası Tara

```
POST /api/category-explorer/scrape-page

Request Body:
{
    "url": "https://www.hepsiburada.com/laptop-c-98",
    "page": 1,
    "session_id": null,
    "page_count": 5
}

Response 200:
{
    "session": {
        "id": "uuid-session",
        "platform": "hepsiburada",
        "category_url": "https://...",
        "category_name": "Laptop",
        "breadcrumbs": [
            {"name": "Elektronik", "url": "https://..."},
            {"name": "Laptop"}
        ],
        "total_products": 120,
        "pages_scraped": 5,
        "status": "completed",
        "created_at": "2026-03-01T11:00:00",
        "product_count": 120
    },
    "pages_scraped_list": [1, 2, 3, 4, 5],
    "page_scraped": 5,
    "products_found": 120,
    "products_added": 120,
    "products_updated": 0,
    "has_next_page": true,
    "total_in_session": 120,
    "products": [ ... ],
    "breadcrumbs": [ ... ]
}
```

### API Çağrısı: Kategori Ürünleri Listele

```
GET /api/category-explorer/products-by-category?page=1&page_size=50&sort_by=position&sort_dir=asc

Tüm Query Parameters:
  page: int              ← default 1
  page_size: int         ← default 50, max 200
  sort_by: string?       ← "position" | "price" | "name" | "rating" | "created_at"
  sort_dir: string?      ← "asc" | "desc"
  platform: string?
  session_id: string?    ← belirli oturum
  category: string?
  search: string?
  brand: string?
  seller: string?
  min_price: float?
  max_price: float?
  min_rating: float?
  is_sponsored: bool?

Response 200:
{
    "total": 120,
    "page": 1,
    "page_size": 50,
    "total_pages": 3,
    "products": [
        {
            "id": 1,
            "session_id": "uuid",
            "name": "Ürün Adı",
            "url": "https://...",
            "image_url": "https://...",
            "brand": "Apple",
            "price": 1299.00,
            "original_price": 1499.00,
            "discount_percentage": 13.3,
            "rating": 4.5,
            "review_count": 567,
            "is_sponsored": false,
            "campaign_text": "Sepette %5 indirim",
            "seller_name": "Satıcı",
            "page_number": 1,
            "position": 3,
            "detail_fetched": true,
            "detail_data": { ... },
            "sku": "HBV001",
            "barcode": "8680001",
            "description": "...",
            "specs": {"RAM": "8GB"},
            "shipping_type": "Ücretsiz",
            "stock_status": "InStock",
            "category_path": "Elektronik > Laptop",
            "seller_list": [
                {"name": "Satıcı A", "id": "abc"},
                {"name": "Satıcı B", "id": "def"}
            ],
            "created_at": "2026-03-01T11:00:00"
        }
    ],
    "filtered_stats": {
        "avg_price": 2345.60,
        "brand_count": 12,
        "seller_count": 34,
        "last_scraped": "2026-03-01T11:00:00"
    },
    "sessions": [ ... ]
}
```

### API Çağrısı: Kategori Filtreleri

```
GET /api/category-explorer/category-filters?session_id=uuid

Response 200:
{
    "brands": ["Apple", "Samsung", "Lenovo", ...],
    "sellers": ["Satıcı A", "Satıcı B", ...],
    "price_range": {"min": 999.00, "max": 45999.00}
}
```

### API Çağrısı: Toplu Detay Çekme

```
POST /api/category-explorer/bulk-fetch

Request Body:
{
    "session_id": "uuid-session",
    "product_ids": null
}

Response 200:
{
    "message": "120 ürün için detay çekme başlatıldı",
    "count": 120
}
```

### API Çağrısı: Detay Çekme Durumu (Polling — 3 saniye)

```
GET /api/category-explorer/fetch-status/{session_id}

Response 200:
{
    "session_id": "uuid",
    "total_products": 120,
    "detail_fetched": 67,
    "pending": 53,
    "is_running": true
}

Polling durma: pending === 0 veya is_running === false
```

### API Çağrısı: Oturumlar

```
GET /api/category-explorer/sessions?platform=hepsiburada&limit=20

Response 200:
{
    "sessions": [
        {
            "id": "uuid",
            "platform": "hepsiburada",
            "category_url": "https://...",
            "category_name": "Laptop",
            "breadcrumbs": [...],
            "total_products": 120,
            "pages_scraped": 5,
            "status": "completed",
            "created_at": "2026-03-01T11:00:00",
            "product_count": 120
        }
    ]
}
```

### Tüm Filtreler (category_page modu)

| Filtre | UI Bileşeni | API Parametresi | Default |
|--------|-------------|-----------------|---------|
| Platform | Pill buttons | `platform` | — |
| Oturum | Picker (session list) | `session_id` | Son oturum |
| Metin arama | TextField | `search` | — |
| Marka | Picker (dinamik) | `brand` | — |
| Satıcı | Picker (dinamik) | `seller` | — |
| Min Fiyat | TextField | `min_price` | — |
| Max Fiyat | TextField | `max_price` | — |
| Min Rating | Picker (4+, 3+, 2+) | `min_rating` | — |
| Sponsorlu | Picker (Tümü/Evet/Hayır) | `is_sponsored` | — |
| Sıralama | Picker | `sort_by` + `sort_dir` | position asc |

### Sıralama Seçenekleri (category_page)

| Label | sort_by | sort_dir |
|-------|---------|----------|
| Sıralama (Sayfa) | `position` | `asc` |
| En Yeni | `created_at` | `desc` |
| Fiyat (Artan) | `price` | `asc` |
| Fiyat (Azalan) | `price` | `desc` |
| Puan (Yüksek) | `rating` | `desc` |
| İsim (A-Z) | `name` | `asc` |

---

## 12. Category Explorer — Ürün Detay

**Web karşılığı:** `components/category-explorer/ProductDetailModal.tsx`

### Ekran Şeması (Sheet — .large detent)

```
┌──────────────────────────────────┐
│  Ürün Detayı               [✕]  │
│                                  │
│  [Ürün Resmi — büyük]           │
│                                  │
│  Ürün Adı Burada                 │
│  Marka: Apple                    │
│  Kategori: Elektronik > Laptop   │
│                                  │
│  ┌────────┐  ┌────────┐        │
│  │ ₺1,299 │  │ ⭐ 4.5 │        │
│  │ Fiyat   │  │ Rating │        │
│  └────────┘  └────────┘        │
│  ┌────────┐  ┌────────┐        │
│  │ 📦Stok │  │ 🚚Ücre.│        │
│  │ Var     │  │ Kargo  │        │
│  └────────┘  └────────┘        │
│                                  │
│  👥 Satıcılar (3)              │
│  ├── Satıcı A - ₺1,299         │
│  ├── Satıcı B - ₺1,350         │
│  └── Satıcı C - ₺1,399         │
│                                  │
│  📋 Özellikler                  │
│  ├── RAM: 8GB                   │
│  ├── Depolama: 256GB            │
│  └── İşlemci: M2                │
│                                  │
│  [📊 Price Monitor'a Ekle]      │
│  [🌐 Pazaryerinde Gör →]        │
└──────────────────────────────────┘
```

### API Çağrısı: Ürün Detayı

```
GET /api/category-explorer/products/{product_id}

Response 200:
{
    "id": 1,
    "session_id": "uuid",
    "name": "Ürün Adı",
    "url": "https://...",
    "image_url": "https://...",
    "brand": "Apple",
    "price": 1299.00,
    "original_price": 1499.00,
    "discount_percentage": 13.3,
    "rating": 4.5,
    "review_count": 567,
    "is_sponsored": false,
    "campaign_text": "",
    "seller_name": "Satıcı A",
    "detail_fetched": true,
    "detail_data": {
        "specs": {"RAM": "8GB", "Depolama": "256GB"},
        "description": "Detaylı açıklama..."
    },
    "sku": "HBV001",
    "barcode": "8680001",
    "description": "Açıklama...",
    "specs": {"RAM": "8GB", "Depolama": "256GB", "İşlemci": "M2"},
    "shipping_type": "Ücretsiz Kargo",
    "stock_status": "InStock",
    "category_path": "Elektronik > Laptop",
    "seller_list": [
        {"name": "Satıcı A", "id": "abc"},
        {"name": "Satıcı B", "id": "def"},
        {"name": "Satıcı C", "id": "ghi"}
    ]
}
```

---

## 13. Settings (Tab 5)

**Web karşılığı:** `pages/Settings.tsx`

### Ekran Şeması

```
┌──────────────────────────────────┐
│  Ayarlar                         │
├──────────────────────────────────┤
│                                  │
│  👤 PROFİL                      │
│  ┌────────────────────────────┐  │
│  │ Ad: Ahmet Yılmaz           │  │
│  │ Email: a@example.com       │  │
│  │ Plan: Pro ●                │  │
│  └────────────────────────────┘  │
│                                  │
│  📦 ABONELİK                    │
│  ┌────────────────────────────┐  │
│  │ Pro Plan — Aktif           │  │
│  │ SKU: 145/1000              │  │
│  │ ████████░░░░ %14.5         │  │
│  │ Tarama: 4x/gün            │  │
│  │                            │  │
│  │ [Plan Değiştir →]          │  │
│  │ [Fatura Yönetimi →]        │  │  ← Safari
│  └────────────────────────────┘  │
│                                  │
│  🔔 BİLDİRİMLER                │
│  ┌────────────────────────────┐  │
│  │ Push Bildirimleri     [◉]  │  │
│  │ Fiyat Alarmları       [◉]  │  │
│  │ Kampanya Uyarıları    [◉]  │  │
│  │ Günlük Özet           [○]  │  │
│  └────────────────────────────┘  │
│                                  │
│  ℹ️ UYGULAMA                    │
│  ┌────────────────────────────┐  │
│  │ Versiyon: 1.0.0            │  │
│  │ Tema: [Sistem ▾]           │  │
│  │ [Geri Bildirim →]          │  │
│  └────────────────────────────┘  │
│                                  │
│  ┌────────────────────────────┐  │
│  │       Çıkış Yap            │  │  ← Destructive
│  └────────────────────────────┘  │
│                                  │
└──────────────────────────────────┘
```

### API Çağrısı: Abonelik Bilgisi

```
GET /api/billing/subscription

Response 200:
{
    "plan_tier": "pro",
    "status": "active",
    "sku_limit": 1000,
    "scan_frequency": "4x/gün",
    "current_sku_count": 145,
    "stripe_subscription_id": "sub_abc123",
    "created_at": "2025-12-01T00:00:00"
}
```

### API Çağrısı: Plan Listesi

```
GET /api/billing/plans

Response 200:
{
    "plans": [
        {
            "tier": "free",
            "name": "Free",
            "price_monthly": 0,
            "currency": "TRY",
            "sku_limit": 10,
            "scan_frequency": "1x/gün (manuel)",
            "platforms": "1 platform",
            "history_days": 7,
            "email_alerts": false,
            "features": ["10 SKU", "1 platform", "Manuel tarama"]
        },
        {
            "tier": "starter",
            "name": "Starter",
            "price_monthly": 299,
            "currency": "TRY",
            "sku_limit": 200,
            "scan_frequency": "2x/gün",
            "platforms": "2 platform",
            "history_days": 30,
            "email_alerts": true,
            "email_alert_limit": 50,
            "features": ["200 SKU", "2 platform", "Otomatik 2x/gün"]
        },
        {
            "tier": "pro",
            "name": "Pro",
            "price_monthly": 899,
            "currency": "TRY",
            "sku_limit": 1000,
            "scan_frequency": "4x/gün",
            "platforms": "Tüm platformlar",
            "history_days": 90,
            "email_alerts": true,
            "email_alert_limit": 200,
            "webhook": true,
            "features": ["1000 SKU", "Tüm platformlar", "4x/gün", "Webhook"]
        },
        {
            "tier": "enterprise",
            "name": "Enterprise",
            "price_monthly": null,
            "currency": "TRY",
            "sku_limit": null,
            "scan_frequency": "24x/gün",
            "platforms": "Tüm platformlar",
            "history_days": null,
            "email_alerts": true,
            "webhook": true,
            "features": ["Sınırsız SKU", "24x/gün", "Öncelikli destek"]
        }
    ]
}
```

### API Çağrısı: Plan Yükselt

```
POST /api/billing/checkout

Request Body:
{
    "plan_tier": "pro",
    "success_url": "marketpulse://billing/success",
    "cancel_url": "marketpulse://billing/cancel"
}

Response 200:
{
    "checkout_url": "https://checkout.stripe.com/c/pay/cs_live_..."
}
```

**iOS:** `SFSafariViewController` ile `checkout_url` açılır.

### API Çağrısı: Fatura Portalı

```
POST /api/billing/portal

Request Body:
{
    "return_url": "marketpulse://settings"
}

Response 200:
{
    "portal_url": "https://billing.stripe.com/p/session/..."
}
```

**iOS:** `SFSafariViewController` ile `portal_url` açılır.

---

## 14. AI Chat (Floating)

**Web karşılığı:** `components/ChatPanel.tsx`

### Ekran Şeması

```
Floating Button (her tab'da):
  ┌──────┐
  │  💬  │  ← overlay, bottom-trailing
  └──────┘

Chat Sheet (.large detent):
┌──────────────────────────────────┐
│  AI Asistan             [✕]     │
│  [+ Yeni] [Geçmiş ▾]           │
├──────────────────────────────────┤
│                                  │
│  ┌────────────────────────────┐  │
│  │ 🤖 Merhaba! Size nasıl     │  │
│  │    yardımcı olabilirim?     │  │
│  └────────────────────────────┘  │
│                                  │
│  Öneriler:                       │
│  ┌──────────────────────┐        │
│  │ Fiyat alarmı olanlar │        │
│  ├──────────────────────┤        │
│  │ En kârlı ürünüm?     │        │
│  ├──────────────────────┤        │
│  │ Rakip fiyat durumu    │        │
│  └──────────────────────┘        │
│                                  │
│  ┌────────────────────────────┐  │
│  │ 👤 En kârlı ürünüm         │  │
│  │    hangisi?                 │  │
│  └────────────────────────────┘  │
│                                  │
│  ┌────────────────────────────┐  │
│  │ 🤖 En kârlı ürününüz       │  │
│  │    "Ürün X" olup %23       │  │
│  │    kâr marjına sahip...     │  │
│  └────────────────────────────┘  │
│                                  │
├──────────────────────────────────┤
│  ┌──────────────────────┐ [📤] │
│  │ Mesajınız...          │      │
│  └──────────────────────┘       │
└──────────────────────────────────┘
```

### API Çağrısı: Mesaj Gönder

```
POST /api/ai/chat

Request Body:
{
    "message": "En kârlı ürünüm hangisi?",
    "conversation_id": "uuid-conv"
}

Response 200:
{
    "response": "En kârlı ürününüz \"Apple AirPods Pro\" olup %23 kâr marjına sahiptir...",
    "conversation_id": "uuid-conv"
}
```

### API Çağrısı: Sohbet Listesi

```
GET /api/ai/conversations

Response 200:
[
    {
        "id": "uuid-conv-1",
        "title": "Fiyat analizi",
        "updated_at": "2026-03-01T14:30:00"
    },
    {
        "id": "uuid-conv-2",
        "title": "Kârlılık soruları",
        "updated_at": "2026-02-28T10:00:00"
    }
]
```

### API Çağrısı: Sohbet Mesajları

```
GET /api/ai/conversations/{conversation_id}/messages

Response 200:
[
    {
        "role": "user",
        "content": "En kârlı ürünüm hangisi?",
        "created_at": "2026-03-01T14:30:00"
    },
    {
        "role": "assistant",
        "content": "En kârlı ürününüz...",
        "created_at": "2026-03-01T14:30:05"
    }
]
```

### API Çağrısı: Sohbet Sil

```
DELETE /api/ai/conversations/{conversation_id}

Response 200:
{
    "status": "ok"
}
```

---

## 15. Mobilde Olmayan Ekranlar (Web-only Referans)

Aşağıdaki ekranlar iOS'a dahil edilmeyecek. Ancak ileri fazlarda eklenebilir.

| Ekran | Web Route | Neden Hariç | API Endpoint'leri |
|-------|-----------|-------------|-------------------|
| **URL Scraper** | `/url-scraper` | Bulk URL girişi mobilde kötü UX | `POST /api/url-scraper/scrape`, `/scrape-bulk`, `/scrape-csv`, `GET /jobs` |
| **Video Transcripts** | `/video-transcripts` | YouTube odaklı araç | `POST /api/transcripts/fetch`, `/fetch-bulk`, `/fetch-csv`, `GET /jobs` |
| **JSON Editor** | `/json-editor` | Kod editörü mobilde uygunsuz | `GET/POST/PUT/DELETE /api/json-editor/files` |
| **Ads (Reklam Analizi)** | `/ads` | Keyword search'e bağımlı | `GET /api/tasks`, `/api/search/{id}/sponsored-*` |
| **Products (Keyword)** | `/products` | Mobilde düşük öncelik | `GET /api/products`, `POST /api/search` |
| **Product Detail** | `/products/:id` | Keyword search'e bağımlı | `GET /api/products/{id}`, `GET .../snapshots`, `POST /api/analyze` |
| **HB/TY/Web Products** | `/hepsiburada`, `/trendyol` | Category Explorer karşılıyor | `GET /api/store-products`, `POST .../scrape-from-*` |
| **Landing Page** | `/landing` | App Store sayfası karşılıyor | Yok |

---

## 16. Ortak TypeScript/Swift Model Eşlemesi

### MonitoredProduct

```
TypeScript                          Swift
─────────────────────────           ─────────────────────────
id: string                     →    let id: String
platform: string               →    let platform: String
sku: string                    →    let sku: String
barcode?: string               →    let barcode: String?
product_url: string            →    let productUrl: String
product_name?: string          →    let productName: String?
brand?: string                 →    let brand: String?
seller_stock_code?: string     →    let sellerStockCode: String?
threshold_price?: number       →    let thresholdPrice: Double?
alert_campaign_price?: number  →    let alertCampaignPrice: Double?
image_url?: string             →    let imageUrl: String?
is_active: boolean             →    let isActive: Bool
last_fetched_at?: string       →    let lastFetchedAt: Date?
seller_count: number           →    let sellerCount: Int
has_price_alert: boolean       →    let hasPriceAlert: Bool
price_alert_count: number      →    let priceAlertCount: Int
has_campaign_alert: boolean    →    let hasCampaignAlert: Bool
campaign_alert_count: number   →    let campaignAlertCount: Int
```

### SellerSnapshot

```
TypeScript                          Swift
─────────────────────────           ─────────────────────────
merchant_id: string            →    let merchantId: String
merchant_name: string          →    let merchantName: String
merchant_logo?: string         →    let merchantLogo: String?
merchant_rating?: number       →    let merchantRating: Double?
merchant_rating_count?: number →    let merchantRatingCount: Int?
merchant_city?: string         →    let merchantCity: String?
price: number                  →    let price: Double
original_price?: number        →    let originalPrice: Double?
minimum_price?: number         →    let minimumPrice: Double?
campaign_price?: number        →    let campaignPrice: Double?
discount_rate?: number         →    let discountRate: Double?
stock_quantity?: number        →    let stockQuantity: Int?
buybox_order?: number          →    let buyboxOrder: Int?
free_shipping: boolean         →    let freeShipping: Bool
fast_shipping: boolean         →    let fastShipping: Bool
is_fulfilled_by_hb: boolean    →    let isFulfilledByHb: Bool
campaigns?: string[]           →    let campaigns: [String]?
snapshot_date: string          →    let snapshotDate: Date
price_alert: boolean           →    let priceAlert: Bool
campaign_alert?: boolean       →    let campaignAlert: Bool?
```

### CodingKeys Pattern

```swift
struct MonitoredProduct: Codable, Identifiable {
    let id: String
    let platform: String
    let sku: String
    // ...

    enum CodingKeys: String, CodingKey {
        case id, platform, sku, barcode, brand
        case productUrl = "product_url"
        case productName = "product_name"
        case sellerStockCode = "seller_stock_code"
        case thresholdPrice = "threshold_price"
        case alertCampaignPrice = "alert_campaign_price"
        case imageUrl = "image_url"
        case isActive = "is_active"
        case lastFetchedAt = "last_fetched_at"
        case sellerCount = "seller_count"
        case hasPriceAlert = "has_price_alert"
        case priceAlertCount = "price_alert_count"
        case hasCampaignAlert = "has_campaign_alert"
        case campaignAlertCount = "campaign_alert_count"
    }
}
```

> **Alternatif:** `JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase` ile otomatik dönüşüm yapılabilir. Bu durumda CodingKeys gerekmez, ama alan adları tam olarak snake_case → camelCase kuralına uymalı.

---

## 17. Tüm Endpoint Özet Tablosu

### iOS'ta Kullanılacak Endpoint'ler

| # | Method | Path | Ekran | Filtreler |
|---|--------|------|-------|-----------|
| 1 | POST | `{SUPABASE}/auth/v1/token?grant_type=password` | Login | — |
| 2 | POST | `{SUPABASE}/auth/v1/signup` | Register | — |
| 3 | POST | `{SUPABASE}/auth/v1/token?grant_type=refresh_token` | Auto-refresh | — |
| 4 | GET | `/api/dashboard/summary` | Dashboard | — |
| 5 | GET | `/api/dashboard/price-movers` | Dashboard | — |
| 6 | GET | `/api/dashboard/profitability-overview` | Dashboard | — |
| 7 | GET | `/api/price-monitor/products` | Price Monitor | platform, search, brand, price_alert_only, campaign_alert_only, limit, offset |
| 8 | GET | `/api/price-monitor/products/{id}` | PM Detay | — |
| 9 | POST | `/api/price-monitor/products` | Import, Onboarding | — |
| 10 | PUT | `/api/price-monitor/products/{id}` | Onboarding, Edit | — |
| 11 | DELETE | `/api/price-monitor/products/{id}` | PM Liste | — |
| 12 | DELETE | `/api/price-monitor/products/bulk/all` | PM Liste | platform |
| 13 | DELETE | `/api/price-monitor/products/bulk/inactive` | PM Liste | platform |
| 14 | POST | `/api/price-monitor/fetch` | Fetch | platform, fetch_type |
| 15 | GET | `/api/price-monitor/fetch/{task_id}` | Fetch Polling | — |
| 16 | POST | `/api/price-monitor/fetch/{task_id}/stop` | Fetch Stop | — |
| 17 | POST | `/api/price-monitor/fetch-single/{id}` | PM Liste | — |
| 18 | GET | `/api/price-monitor/brands` | PM Filtre | platform |
| 19 | GET | `/api/price-monitor/export` | PM Export | platform, active_filter |
| 20 | GET | `/api/price-monitor/products/{id}/price-history` | PM Chart | days, merchant_id |
| 21 | GET | `/api/price-monitor/last-inactive` | PM Liste | platform |
| 22 | POST | `/api/price-monitor/products/import` | CSV Import | platform |
| 23 | GET | `/api/sellers` | Sellers | platform, limit, offset |
| 24 | GET | `/api/sellers/{id}/products` | Seller Detail | platform, price_alert_only, campaign_alert_only |
| 25 | GET | `/api/sellers/{id}/export` | Seller Export | platform, alerts |
| 26 | GET | `/api/store-products` | Category (my) | platform, page, sort_by, sort_dir, search, brand, category, min_price, max_price, min_rating |
| 27 | GET | `/api/store-products/filters` | Category Filters | platform |
| 28 | GET | `/api/store-products/category-tree` | Category Tree | platform |
| 29 | POST | `/api/category-explorer/scrape-page` | Cat. Tarama | — |
| 30 | GET | `/api/category-explorer/sessions` | Cat. Oturumlar | platform |
| 31 | GET | `/api/category-explorer/products-by-category` | Cat. Ürünler | page, sort_by, sort_dir, platform, session_id, category, search, brand, seller, min_price, max_price, min_rating, is_sponsored |
| 32 | GET | `/api/category-explorer/category-filters` | Cat. Filtreler | session_id, category, platform |
| 33 | POST | `/api/category-explorer/bulk-fetch` | Detay Çek | — |
| 34 | GET | `/api/category-explorer/fetch-status/{id}` | Detay Polling | — |
| 35 | GET | `/api/category-explorer/products/{id}` | Ürün Detay | — |
| 36 | DELETE | `/api/category-explorer/sessions/{id}` | Oturum Sil | — |
| 37 | POST | `/api/category-explorer/delete-products` | Toplu Sil | — |
| 38 | GET | `/api/billing/subscription` | Settings | — |
| 39 | GET | `/api/billing/plans` | Settings | — |
| 40 | POST | `/api/billing/checkout` | Settings | — |
| 41 | POST | `/api/billing/portal` | Settings | — |
| 42 | POST | `/api/ai/chat` | AI Chat | — |
| 43 | GET | `/api/ai/conversations` | AI Chat | — |
| 44 | GET | `/api/ai/conversations/{id}/messages` | AI Chat | — |
| 45 | DELETE | `/api/ai/conversations/{id}` | AI Chat | — |
| 46 | GET | `/health` | App Start | — |

**Toplam: 46 endpoint** (3 Supabase Auth + 43 Backend API)

---

## Appendix: Polling Interval Özeti

| Modül | Interval | Endpoint | Durma Koşulu |
|-------|----------|----------|--------------|
| Price Monitor Fetch | 2000ms | `GET /api/price-monitor/fetch/{task_id}` | `status ∈ [completed, failed, stopped]` |
| Category Detail Fetch | 3000ms | `GET /api/category-explorer/fetch-status/{session_id}` | `pending === 0 \|\| is_running === false` |

## Appendix: Debounce Özeti

| Modül | Debounce | Input | Tetiklenen API |
|-------|----------|-------|----------------|
| Price Monitor Search | 400ms | searchText | `GET /api/price-monitor/products?search=` |
| Category Explorer Search | URL sync delay | searchText | `GET /api/store-products?search=` veya `GET /api/category-explorer/products-by-category?search=` |

## Appendix: Pagination Özeti

| Modül | Sayfa Boyutu | Yöntem | Parametre |
|-------|-------------|--------|-----------|
| Price Monitor | 100 | offset-based | `limit=100&offset=N` |
| Sellers | 200 (tümü) | offset-based | `limit=200&offset=0` |
| Seller Detail | 500 (tümü) | offset-based | `limit=500&offset=0` |
| Category Explorer (my) | 50 | page-based | `page=N&page_size=50` |
| Category Explorer (cat) | 50 | page-based | `page=N&page_size=50` |
