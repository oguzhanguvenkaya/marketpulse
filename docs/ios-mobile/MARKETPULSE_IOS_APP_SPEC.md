# MarketPulse iOS App - Teknik Spesifikasyon

> **Versiyon:** 1.0
> **Tarih:** 2026-03-02
> **Hedef:** iOS 17+, Swift 6, SwiftUI, MVVM + Repository Pattern
> **Companion Docs:** `IOS_BACKEND_REQUIREMENTS.md`, `IOS_SCREENS_AND_API_REFERENCE.md`

---

## 1. Proje Genel Bakis

MarketPulse, Turk e-ticaret pazaryerlerinde (Hepsiburada, Trendyol) urun fiyat takibi, rakip analizi ve karlilik hesaplama sunan bir SaaS platformudur. iOS uygulamasi mevcut web platformunun mobil adaptasyonudur ve ayni FastAPI backend'e API uzerinden baglanir.

### 1.1 Temel Ozellikler (iOS)
- **Fiyat Izleme:** SKU bazli fiyat takibi, buybox analizi, fiyat alarmlari
- **Rakip Satici Analizi:** Satici bazli fiyat karsilastirma
- **Kategori Analizi:** Kategori tarama ve urun kesfetme
- **Dashboard:** Ozet istatistikler, fiyat hareketleri, karlilik
- **AI Asistan:** Her ekranda floating chat (SSE streaming)
- **Push Notifications:** Fiyat alarmlari ve kampanya bildirimleri

### 1.2 iOS'ta Yer Almayacak Web Ekranlar
| Web Ekran | Sebep |
|-----------|-------|
| URL Scraper | Desktop araci |
| Video Transcripts | Desktop araci |
| JSON Editor | Desktop araci |
| Ads (Reklam Analizi) | Faz 2 |
| Keyword Products | Faz 2 |
| Product Detail (keyword bazli) | Faz 2 |
| HB/TY/Web Products | Category Explorer'a entegre |
| Landing Page | App Store sayfasi yeterli |

---

## 2. Mimari: MVVM + Repository

```
┌─────────────────────────────────────────────────┐
│                    SwiftUI View                  │
│  (Screen / Component)                            │
├─────────────────────────────────────────────────┤
│                   ViewModel                      │
│  (@Observable, business logic, state)            │
├─────────────────────────────────────────────────┤
│                  Repository                      │
│  (data orchestration, caching)                   │
├─────────────────────────────────────────────────┤
│                  APIClient                       │
│  (URLSession, JWT auth, error handling)          │
├─────────────────────────────────────────────────┤
│              Backend (FastAPI)                    │
│              Supabase Auth                        │
└─────────────────────────────────────────────────┘
```

### 2.1 Katman Kurallari
- **View:** Sadece UI rendering ve user interaction. State yok (ViewModel'den okur).
- **ViewModel:** `@Observable` macro, business logic, Repository cagirilari. Her ekranin kendi ViewModel'i var.
- **Repository:** Data kaynaklarini (API, cache, Keychain) orkestra eder. Protocol-based (test icin mock'lanabilir).
- **APIClient:** Singleton `actor`. URLSession, JWT token injection, refresh logic, error mapping.

### 2.2 Dependency Injection
```swift
// Protocol tabanli DI
protocol PriceMonitorRepositoryProtocol {
    func getProducts(platform: String, params: ProductQueryParams) async throws -> MonitoredProductsResponse
    func startFetchTask(platform: String, fetchType: FetchType) async throws -> FetchTaskResponse
    // ...
}

// Production implementation
final class PriceMonitorRepository: PriceMonitorRepositoryProtocol {
    private let apiClient: APIClient
    init(apiClient: APIClient = .shared) { self.apiClient = apiClient }
}

// Test mock
final class MockPriceMonitorRepository: PriceMonitorRepositoryProtocol { ... }
```

---

## 3. Navigasyon Yapisi

```
TabView (5 tab)
├── Tab 1: Dashboard
│   └── DashboardView
│       ├── SKU Overview Card
│       ├── Alerts Card
│       ├── Price Movers Card (drops / increases)
│       └── Profitability Overview Card
│
├── Tab 2: Price Monitor (Fiyat Izleme)
│   ├── PriceMonitorListView
│   │   ├── Platform Segmented Control (HB / Trendyol)
│   │   ├── Search Bar (400ms debounce)
│   │   ├── Filter Bar (brand, alarm, campaign)
│   │   ├── Product List (LazyVStack, pagination offset=100)
│   │   └── Toolbar: Import, Fetch, Export, Delete
│   └── PriceMonitorDetailView (NavigationLink push)
│       ├── Product Info Header
│       ├── Price Chart (Swift Charts, 30 gun)
│       ├── Seller List (buybox sirasina gore)
│       └── Threshold Edit Sheet
│
├── Tab 3: Sellers (Saticilar)
│   ├── SellerListView
│   │   ├── Platform Segmented Control
│   │   └── Seller Cards (logo, name, product count, avg price)
│   └── SellerDetailView (push)
│       ├── Seller Info Header
│       ├── Product List
│       └── Export Button
│
├── Tab 4: Category Explorer (Kategori Analizi)
│   ├── CategoryExplorerView
│   │   ├── Platform Picker
│   │   ├── View Mode Segmented (My Products / Category Page)
│   │   ├── Category Tree (sidebar veya drill-down)
│   │   ├── Product Grid/List
│   │   └── Filters Sheet
│   └── CategoryProductDetailView (push)
│
└── Tab 5: Settings (Ayarlar)
    ├── Profile Section
    ├── Subscription Section (plan tier, SKU usage)
    ├── Notification Preferences
    ├── Scheduled Tasks
    └── Logout Button

Floating Overlay (her tab'da):
└── AIChatView (sheet / overlay)
    ├── Conversation List
    ├── Chat Messages (SSE streaming)
    └── Context-aware suggestions
```

### 3.1 Navigation Stack
```swift
@main
struct MarketPulseApp: App {
    @State private var authManager = AuthManager()

    var body: some Scene {
        WindowGroup {
            if authManager.isAuthenticated {
                MainTabView()
                    .environment(authManager)
            } else {
                AuthView()
                    .environment(authManager)
            }
        }
    }
}

struct MainTabView: View {
    @State private var selectedTab = 0
    @State private var showAIChat = false

    var body: some View {
        ZStack {
            TabView(selection: $selectedTab) {
                NavigationStack { DashboardView() }
                    .tabItem { Label("Dashboard", systemImage: "chart.bar") }
                    .tag(0)

                NavigationStack { PriceMonitorListView() }
                    .tabItem { Label("Fiyat Izleme", systemImage: "tag") }
                    .tag(1)

                NavigationStack { SellerListView() }
                    .tabItem { Label("Saticilar", systemImage: "person.2") }
                    .tag(2)

                NavigationStack { CategoryExplorerView() }
                    .tabItem { Label("Kategoriler", systemImage: "square.grid.2x2") }
                    .tag(3)

                NavigationStack { SettingsView() }
                    .tabItem { Label("Ayarlar", systemImage: "gearshape") }
                    .tag(4)
            }

            // Floating AI Chat Button
            VStack {
                Spacer()
                HStack {
                    Spacer()
                    AIChatFloatingButton(isPresented: $showAIChat)
                        .padding(.trailing, 20)
                        .padding(.bottom, 90)
                }
            }
        }
        .sheet(isPresented: $showAIChat) {
            AIChatView()
        }
    }
}
```

---

## 4. Ekran Detaylari

### 4.1 Auth Ekranlari

#### LoginView
```
┌────────────────────────────┐
│        MarketPulse         │
│         [Logo]             │
│                            │
│  ┌──────────────────────┐  │
│  │ E-posta              │  │
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │ Sifre                │  │
│  └──────────────────────┘  │
│                            │
│  ┌──────────────────────┐  │
│  │     Giris Yap        │  │
│  └──────────────────────┘  │
│                            │
│  Hesabin yok mu? Kayit Ol  │
└────────────────────────────┘
```

**API:** `POST {SUPABASE_URL}/auth/v1/token?grant_type=password`
- Body: `{ "email": "...", "password": "..." }`
- Headers: `apikey: {SUPABASE_ANON_KEY}`
- Response: `{ "access_token", "refresh_token", "expires_in", "user": { "id", "email" } }`

#### RegisterView
```
┌────────────────────────────┐
│        MarketPulse         │
│  ┌──────────────────────┐  │
│  │ Ad Soyad             │  │
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │ E-posta              │  │
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │ Sifre                │  │
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │ Sifre Tekrar         │  │
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │     Kayit Ol         │  │
│  └──────────────────────┘  │
│  Hesabin var mi? Giris Yap │
└────────────────────────────┘
```

**API:** `POST {SUPABASE_URL}/auth/v1/signup`
- Body: `{ "email": "...", "password": "...", "data": { "full_name": "..." } }`

### 4.2 Onboarding (Ilk Giris)

4 adimli onboarding — sadece ilk giriste gosterilir.

```
Adim 1: Hosgeldin
  "MarketPulse ile rakiplerinizi takip edin"
  [Illustration]

Adim 2: Platform Secimi
  ○ Hepsiburada
  ○ Trendyol
  ○ Her ikisi

Adim 3: Ilk Urun Ekleme
  "SKU veya urun URL'si girin"
  [TextField] + [Ekle Button]
  (veya) "Sonra ekle" link

Adim 4: Hazirsiniz!
  "Dashboard'a git" button
```

**State:** `UserDefaults` key: `onboarding_completed`. Gelecekte backend sync (`GET/PUT /api/user/onboarding-status`).

### 4.3 Dashboard

```
┌────────────────────────────────────────┐
│ Dashboard                    [AI Chat] │
├────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐      │
│ │ Toplam SKU   │ │ Alarmlar     │      │
│ │   45 / 200   │ │   3 bugun    │      │
│ │ ██████░░ 23% │ │              │      │
│ └──────────────┘ └──────────────┘      │
│                                        │
│ ┌──────────────┐ ┌──────────────┐      │
│ │ Plan: Pro    │ │ Son Tarama   │      │
│ │ 1000 SKU     │ │ 2 saat once  │      │
│ └──────────────┘ └──────────────┘      │
│                                        │
│ Fiyat Dususler            Tumu >       │
│ ┌──────────────────────────────┐       │
│ │ Urun A    ₺120 → ₺95  -21% │       │
│ │ Urun B    ₺80 → ₺72   -10% │       │
│ └──────────────────────────────┘       │
│                                        │
│ Fiyat Artislar            Tumu >       │
│ ┌──────────────────────────────┐       │
│ │ Urun C    ₺50 → ₺65   +30% │       │
│ └──────────────────────────────┘       │
│                                        │
│ Karlilik Ozeti           Tumu >        │
│ ┌──────────────────────────────┐       │
│ │ En Karli: Urun X  +₺45.2    │       │
│ │ En Zararli: Urun Y -₺12.8   │       │
│ └──────────────────────────────┘       │
└────────────────────────────────────────┘
```

**API Calls:**
1. `GET /api/dashboard/summary` — SKU overview, alarmlar, plan, son tarama
2. `GET /api/dashboard/price-movers` — Fiyat dususler/artislar (son 7 gun)
3. `GET /api/dashboard/profitability-overview` — Karlilik ozeti

**Refresh:** Pull-to-refresh ile 3 endpoint paralel cagirilir.

### 4.4 Price Monitor (Fiyat Izleme)

```
┌────────────────────────────────────────┐
│ Fiyat Izleme                           │
├────────────────────────────────────────┤
│ ┌─HB──┬──TY─┐  [Import] [Fetch ▼]    │
│ └──────┴─────┘  [Export] [Delete ▼]   │
│                                        │
│ ┌──────────────────────────────┐       │
│ │ 🔍 Urun ara...              │       │
│ └──────────────────────────────┘       │
│                                        │
│ [Marka ▼]  [⚠ Alarm]  [🏷 Kampanya]  │
│ [Aktif: 45]  [Inaktif: 3]             │
│                                        │
│ ┌──────────────────────────────┐       │
│ │ [img] Urun Adi              │       │
│ │       SKU: ABC123            │       │
│ │       Buybox: ₺129.90       │       │
│ │       Satici: MagazaX        │       │
│ │       Esik: ₺120  ⚠ ALARM  │       │
│ │       5 satici               │  >    │
│ └──────────────────────────────┘       │
│ ┌──────────────────────────────┐       │
│ │ [img] Urun Adi 2            │       │
│ │       ...                    │  >    │
│ └──────────────────────────────┘       │
│         [Daha Fazla Yukle]             │
└────────────────────────────────────────┘
```

**API Calls:**
- `GET /api/price-monitor/products?platform=hepsiburada&limit=100&offset=0&brand=&price_alert_only=false&campaign_alert_only=false&search=`
- `GET /api/price-monitor/brands?platform=hepsiburada`
- `POST /api/price-monitor/products` (import)
- `POST /api/price-monitor/fetch` → `GET /api/price-monitor/fetch/{task_id}` (polling 2s)
- `GET /api/price-monitor/export?platform=hepsiburada&active_filter=all`
- `DELETE /api/price-monitor/products/{id}`
- `DELETE /api/price-monitor/products/bulk/all`
- `DELETE /api/price-monitor/products/bulk/inactive`

**Filtreler:**

| Filtre | UI | API Param |
|--------|-----|-----------|
| Platform | Segmented Control | `platform` |
| Marka | Dropdown (from brands API) | `brand` |
| Fiyat Alarm | Toggle | `price_alert_only` |
| Kampanya Alarm | Toggle | `campaign_alert_only` |
| Arama | TextField (400ms debounce) | `search` |
| Inaktif Goster | Toggle | `show_inactive` |

**Pagination:** Offset-based, `limit=100`, "Daha Fazla Yukle" button.

**Polling Pattern:**
```swift
// Fetch task polling
func pollFetchStatus(taskId: String) {
    Timer.publish(every: 2.0, on: .main, in: .common)
        .autoconnect()
        .sink { _ in
            Task {
                let status = try await repository.getFetchStatus(taskId)
                if ["completed", "failed", "stopped"].contains(status.status) {
                    // timer cancel + reload products
                }
            }
        }
}
```

### 4.5 Price Monitor Detail

```
┌────────────────────────────────────────┐
│ < Geri          Urun Detay             │
├────────────────────────────────────────┤
│ ┌──────────────────────────────┐       │
│ │         [Urun Gorseli]       │       │
│ │                              │       │
│ │ Urun Adi Burada              │       │
│ │ SKU: ABC123 | HB             │       │
│ │ Marka: BrandX                │       │
│ └──────────────────────────────┘       │
│                                        │
│ Fiyat Esikleri              [Duzenle]  │
│ ┌──────────────────────────────┐       │
│ │ Alarm Esigi:  ₺120.00       │       │
│ │ Kampanya:     ₺110.00       │       │
│ │ Maliyet:      ₺80.00        │       │
│ └──────────────────────────────┘       │
│                                        │
│ Fiyat Gecmisi (30 Gun)                 │
│ ┌──────────────────────────────┐       │
│ │   📈 Swift Charts Line       │       │
│ │   (price over time)          │       │
│ └──────────────────────────────┘       │
│                                        │
│ Saticilar (buybox sirasi)              │
│ ┌──────────────────────────────┐       │
│ │ 🏆 1. SaticiA  ₺129.90      │       │
│ │    ⭐ 9.2 | Ucretsiz Kargo   │       │
│ ├──────────────────────────────┤       │
│ │ 2. SaticiB     ₺134.50      │       │
│ │    ⭐ 8.8 | Kargo: ₺19.90   │       │
│ ├──────────────────────────────┤       │
│ │ 3. SaticiC     ₺139.00      │       │
│ │    ⭐ 7.5                    │       │
│ └──────────────────────────────┘       │
└────────────────────────────────────────┘
```

**API Calls:**
- `GET /api/price-monitor/products/{id}` — Urun + saticilar
- `GET /api/price-monitor/products/{id}/price-history?days=30` — Grafik verisi
- `PUT /api/price-monitor/products/{id}` — Esik guncelleme

### 4.6 Sellers (Saticilar)

```
┌────────────────────────────────────────┐
│ Saticilar                              │
├────────────────────────────────────────┤
│ ┌─HB──┬──TY─┐                         │
│ └──────┴─────┘                         │
│                                        │
│ ┌──────────────────────────────┐       │
│ │ [logo] SaticiAdi             │       │
│ │        12 urun | Ort: ₺145   │  >    │
│ ├──────────────────────────────┤       │
│ │ [logo] SaticiAdi2            │       │
│ │        8 urun | Ort: ₺230    │  >    │
│ └──────────────────────────────┘       │
└────────────────────────────────────────┘
```

**API:** `GET /api/sellers?platform=hepsiburada&limit=200&offset=0`

**Logo Fallback:** HB logolari genelde gelir. Trendyol'da null — initials avatar veya SF Symbol placeholder.

### 4.7 Seller Detail

```
┌────────────────────────────────────────┐
│ < Geri         SaticiAdi               │
├────────────────────────────────────────┤
│ ┌──────────────────────────────┐       │
│ │ [logo]  SaticiAdi            │       │
│ │ ⭐ 9.2 (1,234 degerlendirme) │       │
│ │ 📍 Istanbul                  │       │
│ │ 12 takip edilen urun         │       │
│ └──────────────────────────────┘       │
│                                        │
│ [⚠ Alarm] [🏷 Kampanya] [Export CSV]  │
│                                        │
│ ┌──────────────────────────────┐       │
│ │ Urun 1        ₺129.90       │       │
│ │ Buybox: #1    Stok: 50       │       │
│ ├──────────────────────────────┤       │
│ │ Urun 2        ₺89.90        │       │
│ │ Buybox: #3    ⚠ Esik alti   │       │
│ └──────────────────────────────┘       │
└────────────────────────────────────────┘
```

**API:** `GET /api/sellers/{merchant_id}/products?platform=hepsiburada&price_alert_only=false&campaign_alert_only=false`

### 4.8 Category Explorer

```
┌────────────────────────────────────────┐
│ Kategori Analizi                       │
├────────────────────────────────────────┤
│ ┌─HB──┬──TY─┐                         │
│ └──────┴─────┘                         │
│ ┌─Urunlerim─┬──Kategori Sayfasi─┐     │
│ └────────────┴───────────────────┘     │
│                                        │
│ [Kategori Agaci]                       │
│ ├── Elektronik (245)                   │
│ │   ├── Telefon (120)                  │
│ │   └── Tablet (45)                    │
│ ├── Giyim (180)                        │
│ └── Ev & Yasam (90)                    │
│                                        │
│ ┌──────────────────────────────┐       │
│ │ 🔍 Urun ara...              │       │
│ └──────────────────────────────┘       │
│ [Marka ▼] [Fiyat ▼] [Siralama ▼]     │
│                                        │
│ ┌─────────┐ ┌─────────┐               │
│ │ [img]   │ │ [img]   │               │
│ │ Urun 1  │ │ Urun 2  │               │
│ │ ₺129.90 │ │ ₺89.50  │               │
│ │ ⭐ 4.2   │ │ ⭐ 4.8   │               │
│ └─────────┘ └─────────┘               │
│                                        │
│ [Sayfa: 1/20]  [< Onceki] [Sonraki >] │
└────────────────────────────────────────┘
```

**Iki Mod:**
1. **Urunlerim (my_products):** Kullanicinin kendi magaza urunleri (StoreProduct tablosu)
2. **Kategori Sayfasi (category_page):** Scrape edilen kategori sayfa urunleri

**API Calls (my_products):**
- `GET /api/store-products?platform=hepsiburada&page=1&page_size=50&search=&category=&brand=&min_price=&max_price=&min_rating=&sort_by=price&sort_dir=asc`
- `GET /api/store-products/filters?platform=hepsiburada`
- `GET /api/store-products/category-tree?platform=hepsiburada`
- `GET /api/store-products/stats`

**API Calls (category_page):**
- `POST /api/category-explorer/scrape` — Kategori sayfasi tara
- `GET /api/category-explorer/sessions` — Oturum listesi
- `GET /api/category-explorer/products-by-category?session_id=&page=1&page_size=50&brand=&seller=&min_price=&max_price=&sort_by=price&sort_dir=asc`
- `GET /api/category-explorer/category-filters?session_id=`
- `POST /api/category-explorer/fetch-details` — Detay bilgi cek
- `GET /api/category-explorer/fetch-status/{session_id}` — Polling 3s

**Pagination:** Page-based, `page_size=50`.

### 4.9 Settings (Ayarlar)

```
┌────────────────────────────────────────┐
│ Ayarlar                                │
├────────────────────────────────────────┤
│ Profil                                 │
│ ┌──────────────────────────────┐       │
│ │ Ad: Mehmet Yilmaz            │       │
│ │ Email: mehmet@firma.com      │       │
│ └──────────────────────────────┘       │
│                                        │
│ Abonelik                               │
│ ┌──────────────────────────────┐       │
│ │ Plan: Pro (₺899/ay)         │       │
│ │ SKU: 45 / 1000              │       │
│ │ Tarama: 4x/gun              │       │
│ │ [Plan Degistir]             │       │
│ └──────────────────────────────┘       │
│                                        │
│ Bildirimler                            │
│ ┌──────────────────────────────┐       │
│ │ Push Bildirimler     [ON]   │       │
│ │ Fiyat Alarmlari      [ON]   │       │
│ │ Kampanya Alarmlari   [ON]   │       │
│ │ Gunluk Ozet          [OFF]  │       │
│ └──────────────────────────────┘       │
│                                        │
│ Zamanlanmis Gorevler                   │
│ ┌──────────────────────────────┐       │
│ │ HB Fiyat Tarama  Her 6 saat │       │
│ │ TY Fiyat Tarama  Her 12 saat│       │
│ │ [Yeni Gorev Ekle]           │       │
│ └──────────────────────────────┘       │
│                                        │
│ [Cikis Yap]                           │
└────────────────────────────────────────┘
```

**API Calls:**
- `GET /api/billing/subscription` — Abonelik bilgisi
- `GET /api/billing/plans` — Plan listesi
- `POST /api/billing/checkout` → Safari'de Stripe Checkout
- `POST /api/billing/portal` → Safari'de Stripe Portal
- `GET /api/scheduler/tasks` — Zamanlanmis gorevler
- `POST /api/scheduler/tasks` — Yeni gorev
- `PUT /api/scheduler/tasks/{id}` — Gorev guncelle
- `DELETE /api/scheduler/tasks/{id}` — Gorev sil

### 4.10 AI Chat (Floating Overlay)

```
┌────────────────────────────────────────┐
│ AI Asistan             [X] [Yeni Chat] │
├────────────────────────────────────────┤
│                                        │
│    ┌──────────────────────┐            │
│    │ Kullanici mesaji     │            │
│    └──────────────────────┘            │
│ ┌──────────────────────┐               │
│ │ AI yaniti (streaming) │               │
│ │ ...typing             │               │
│ └──────────────────────┘               │
│                                        │
│ Oneriler:                              │
│ [En cok dusen urunler?]               │
│ [Bu saticiyi analiz et]               │
│                                        │
├────────────────────────────────────────┤
│ ┌──────────────────────────┐ [Gonder] │
│ │ Mesajinizi yazin...      │          │
│ └──────────────────────────┘          │
└────────────────────────────────────────┘
```

**API:** `POST /api/ai/chat/stream` (SSE)
- Body: `{ "message": "...", "conversation_id": "...", "context": { "page": "price_monitor", "product_id": "..." } }`
- SSE Events: `token`, `tool_start`, `tool_done`, `done`, `error`

**Context-Aware:** Aktif ekrana gore farkli oneriler ve context gonderilir.

---

## 5. Swift Data Modelleri

### 5.1 Auth Models
```swift
struct AuthResponse: Codable {
    let accessToken: String
    let refreshToken: String
    let expiresIn: Int
    let user: AuthUser

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
        case user
    }
}

struct AuthUser: Codable {
    let id: String
    let email: String
    let userMetadata: UserMetadata?

    enum CodingKeys: String, CodingKey {
        case id, email
        case userMetadata = "user_metadata"
    }
}

struct UserMetadata: Codable {
    let fullName: String?

    enum CodingKeys: String, CodingKey {
        case fullName = "full_name"
    }
}
```

### 5.2 Price Monitor Models
```swift
struct MonitoredProduct: Codable, Identifiable {
    let id: String
    let platform: String
    let sku: String
    let barcode: String?
    let productUrl: String
    let productName: String?
    let brand: String?
    let sellerStockCode: String?
    let thresholdPrice: Double?
    let alertCampaignPrice: Double?
    let unitCost: Double?
    let shippingCost: Double?
    let imageUrl: String?
    let isActive: Bool
    let createdAt: String
    let updatedAt: String?
    let lastFetchedAt: String?

    // Computed from SellerSnapshot (buybox_order=1)
    let currentPrice: Double?
    let sellerCount: Int?
    let buyboxSeller: String?

    enum CodingKeys: String, CodingKey {
        case id, platform, sku, barcode, brand
        case productUrl = "product_url"
        case productName = "product_name"
        case sellerStockCode = "seller_stock_code"
        case thresholdPrice = "threshold_price"
        case alertCampaignPrice = "alert_campaign_price"
        case unitCost = "unit_cost"
        case shippingCost = "shipping_cost"
        case imageUrl = "image_url"
        case isActive = "is_active"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case lastFetchedAt = "last_fetched_at"
        case currentPrice = "current_price"
        case sellerCount = "seller_count"
        case buyboxSeller = "buybox_seller"
    }
}

struct MonitoredProductsResponse: Codable {
    let products: [MonitoredProduct]
    let total: Int
    let activeTotal: Int?
    let inactiveTotal: Int?
    let platform: String
    let limit: Int
    let offset: Int

    enum CodingKeys: String, CodingKey {
        case products, total, platform, limit, offset
        case activeTotal = "active_total"
        case inactiveTotal = "inactive_total"
    }
}

struct SellerSnapshot: Codable, Identifiable {
    let id: Int
    let merchantId: String?
    let merchantName: String?
    let merchantLogo: String?
    let merchantRating: Double?
    let merchantRatingCount: Int?
    let merchantCity: String?
    let price: Double
    let originalPrice: Double?
    let minimumPrice: Double?
    let discountRate: Double?
    let stockQuantity: Int?
    let buyboxOrder: Int?
    let freeShipping: Bool?
    let fastShipping: Bool?
    let isFulfilledByHb: Bool?
    let deliveryInfo: String?
    let campaignInfo: String?
    let campaigns: [CampaignTag]?
    let campaignPrice: Double?
    let snapshotDate: String

    enum CodingKeys: String, CodingKey {
        case id, price, campaigns
        case merchantId = "merchant_id"
        case merchantName = "merchant_name"
        case merchantLogo = "merchant_logo"
        case merchantRating = "merchant_rating"
        case merchantRatingCount = "merchant_rating_count"
        case merchantCity = "merchant_city"
        case originalPrice = "original_price"
        case minimumPrice = "minimum_price"
        case discountRate = "discount_rate"
        case stockQuantity = "stock_quantity"
        case buyboxOrder = "buybox_order"
        case freeShipping = "free_shipping"
        case fastShipping = "fast_shipping"
        case isFulfilledByHb = "is_fulfilled_by_hb"
        case deliveryInfo = "delivery_info"
        case campaignInfo = "campaign_info"
        case campaignPrice = "campaign_price"
        case snapshotDate = "snapshot_date"
    }
}

struct CampaignTag: Codable {
    let name: String?
    let type: String?
    let badge: String?
}

struct FetchTaskResponse: Codable {
    let taskId: String
    let platform: String
    let fetchType: String?
    let status: String
    let message: String?
    let executor: String?

    enum CodingKeys: String, CodingKey {
        case platform, status, message, executor
        case taskId = "task_id"
        case fetchType = "fetch_type"
    }
}

struct FetchTaskStatus: Codable {
    let taskId: String
    let status: String
    let totalProducts: Int
    let completedProducts: Int
    let failedProducts: Int
    let fetchType: String?
    let lastInactiveCount: Int?

    enum CodingKeys: String, CodingKey {
        case status
        case taskId = "task_id"
        case totalProducts = "total_products"
        case completedProducts = "completed_products"
        case failedProducts = "failed_products"
        case fetchType = "fetch_type"
        case lastInactiveCount = "last_inactive_count"
    }
}

enum FetchType: String, Codable {
    case active
    case inactive
    case lastInactive = "last_inactive"
}
```

### 5.3 Dashboard Models
```swift
struct DashboardSummary: Codable {
    let skuOverview: SKUOverview
    let alerts: AlertsSummary
    let plan: PlanInfo
    let lastScan: LastScanInfo
    let recentSearches: [RecentSearch]

    enum CodingKeys: String, CodingKey {
        case alerts, plan
        case skuOverview = "sku_overview"
        case lastScan = "last_scan"
        case recentSearches = "recent_searches"
    }
}

struct SKUOverview: Codable {
    let total: Int
    let limit: Int
    let usagePercent: Double
    let byPlatform: [String: Int]

    enum CodingKeys: String, CodingKey {
        case total, limit
        case usagePercent = "usage_percent"
        case byPlatform = "by_platform"
    }
}

struct AlertsSummary: Codable {
    let todayCount: Int
    let thresholdViolations: [ThresholdViolation]

    enum CodingKeys: String, CodingKey {
        case todayCount = "today_count"
        case thresholdViolations = "threshold_violations"
    }
}

struct ThresholdViolation: Codable, Identifiable {
    let productId: String
    let productName: String?
    let sku: String?
    let platform: String?
    let currentPrice: Double
    let thresholdPrice: Double
    let seller: String?

    var id: String { productId }

    enum CodingKeys: String, CodingKey {
        case sku, platform, seller
        case productId = "product_id"
        case productName = "product_name"
        case currentPrice = "current_price"
        case thresholdPrice = "threshold_price"
    }
}

struct PriceMover: Codable, Identifiable {
    let productId: String
    let productName: String?
    let sku: String?
    let platform: String?
    let oldPrice: Double
    let newPrice: Double
    let changePercent: Double
    let direction: String  // "up" | "down"

    var id: String { productId }

    enum CodingKeys: String, CodingKey {
        case sku, platform, direction
        case productId = "product_id"
        case productName = "product_name"
        case oldPrice = "old_price"
        case newPrice = "new_price"
        case changePercent = "change_percent"
    }
}

struct PriceMoversResponse: Codable {
    let priceDrops: [PriceMover]
    let priceIncreases: [PriceMover]

    enum CodingKeys: String, CodingKey {
        case priceDrops = "price_drops"
        case priceIncreases = "price_increases"
    }
}
```

### 5.4 Seller Models
```swift
struct SellerInfo: Codable, Identifiable {
    let merchantId: String
    let merchantName: String
    let merchantLogo: String?
    let merchantRating: Double?
    let merchantRatingCount: Int?
    let merchantCity: String?
    let productCount: Int
    let avgPrice: Double?
    let platform: String

    var id: String { merchantId }

    enum CodingKeys: String, CodingKey {
        case platform
        case merchantId = "merchant_id"
        case merchantName = "merchant_name"
        case merchantLogo = "merchant_logo"
        case merchantRating = "merchant_rating"
        case merchantRatingCount = "merchant_rating_count"
        case merchantCity = "merchant_city"
        case productCount = "product_count"
        case avgPrice = "avg_price"
    }
}

struct SellersResponse: Codable {
    let sellers: [SellerInfo]
    let total: Int
    let platform: String
}

struct SellerProductsResponse: Codable {
    let products: [MonitoredProduct]
    let seller: SellerInfo?
    let total: Int
}
```

### 5.5 Category Models
```swift
struct CategoryTreeNode: Codable, Identifiable {
    let name: String
    let path: String
    let count: Int
    let children: [CategoryTreeNode]?

    var id: String { path }
}

struct CategoryProductItem: Codable, Identifiable {
    let id: Int
    let productName: String?
    let brand: String?
    let price: Double?
    let originalPrice: Double?
    let rating: Double?
    let ratingCount: Int?
    let imageUrl: String?
    let sellerName: String?
    let productUrl: String?
    let isSponsored: Bool?
    let detailFetched: Bool?

    enum CodingKeys: String, CodingKey {
        case id, brand, price, rating
        case productName = "product_name"
        case originalPrice = "original_price"
        case ratingCount = "rating_count"
        case imageUrl = "image_url"
        case sellerName = "seller_name"
        case productUrl = "product_url"
        case isSponsored = "is_sponsored"
        case detailFetched = "detail_fetched"
    }
}

struct CategoryProductListResponse: Codable {
    let products: [CategoryProductItem]
    let total: Int
    let page: Int
    let pageSize: Int
    let totalPages: Int

    enum CodingKeys: String, CodingKey {
        case products, total, page
        case pageSize = "page_size"
        case totalPages = "total_pages"
    }
}
```

### 5.6 AI Chat Models
```swift
struct ChatMessage: Codable, Identifiable {
    let id: String?
    let role: String       // "user" | "assistant" | "tool"
    let content: String
    let toolCalls: [ToolCall]?
    let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case id, role, content
        case toolCalls = "tool_calls"
        case createdAt = "created_at"
    }
}

struct ChatConversation: Codable, Identifiable {
    let id: String
    let title: String?
    let createdAt: String
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, title
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct ChatRequest: Codable {
    let message: String
    let conversationId: String?
    let context: ChatContext?

    enum CodingKeys: String, CodingKey {
        case message, context
        case conversationId = "conversation_id"
    }
}

struct ChatContext: Codable {
    let page: String
    let productId: String?
    let sku: String?
    let productName: String?
    let platform: String?
    let merchantId: String?
    let sellerName: String?

    enum CodingKeys: String, CodingKey {
        case page, sku, platform
        case productId = "product_id"
        case productName = "product_name"
        case merchantId = "merchant_id"
        case sellerName = "seller_name"
    }
}
```

---

## 6. Networking Layer

### 6.1 APIClient (Actor)
```swift
actor APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let baseURL: URL
    private let decoder: JSONDecoder

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 300
        self.session = URLSession(configuration: config)

        #if DEBUG
        self.baseURL = URL(string: "http://localhost:8000/api")!
        #else
        self.baseURL = URL(string: "https://your-production-url.com/api")!
        #endif

        self.decoder = JSONDecoder()
    }

    // MARK: - Generic Request

    func request<T: Decodable>(
        _ method: HTTPMethod,
        path: String,
        queryItems: [URLQueryItem]? = nil,
        body: Encodable? = nil
    ) async throws -> T {
        var urlComponents = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        urlComponents.queryItems = queryItems?.filter { $0.value != nil }

        var request = URLRequest(url: urlComponents.url!)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // JWT Token injection
        if let token = await AuthManager.shared.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return try decoder.decode(T.self, from: data)
        case 401:
            // Token refresh attempt
            try await AuthManager.shared.refreshToken()
            // Retry once
            return try await retryRequest(method, path: path, queryItems: queryItems, body: body)
        case 403:
            throw APIError.forbidden
        case 404:
            throw APIError.notFound
        case 422:
            let detail = try? decoder.decode(ValidationError.self, from: data)
            throw APIError.validation(detail?.detail ?? "Validation error")
        default:
            let detail = try? decoder.decode(ErrorResponse.self, from: data)
            throw APIError.server(httpResponse.statusCode, detail?.detail ?? "Server error")
        }
    }

    // MARK: - SSE Stream (AI Chat)

    func streamChat(request: ChatRequest) -> AsyncThrowingStream<SSEEvent, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    let url = baseURL.appendingPathComponent("ai/chat/stream")
                    var urlRequest = URLRequest(url: url)
                    urlRequest.httpMethod = "POST"
                    urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    urlRequest.setValue("text/event-stream", forHTTPHeaderField: "Accept")

                    if let token = await AuthManager.shared.accessToken {
                        urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
                    }

                    urlRequest.httpBody = try JSONEncoder().encode(request)

                    let (bytes, _) = try await session.bytes(for: urlRequest)

                    for try await line in bytes.lines {
                        if line.hasPrefix("data: ") {
                            let jsonStr = String(line.dropFirst(6))
                            if let data = jsonStr.data(using: .utf8),
                               let event = try? JSONDecoder().decode(SSEEvent.self, from: data) {
                                continuation.yield(event)
                                if event.type == "done" || event.type == "error" {
                                    continuation.finish()
                                    return
                                }
                            }
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    // MARK: - File Download (Export)

    func downloadFile(path: String, queryItems: [URLQueryItem]? = nil) async throws -> URL {
        var urlComponents = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        urlComponents.queryItems = queryItems

        var request = URLRequest(url: urlComponents.url!)
        if let token = await AuthManager.shared.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (tempURL, _) = try await session.download(for: request)

        let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let destinationURL = documentsURL.appendingPathComponent("export_\(Date().timeIntervalSince1970).csv")
        try FileManager.default.moveItem(at: tempURL, to: destinationURL)

        return destinationURL
    }
}

// MARK: - Supporting Types

enum HTTPMethod: String {
    case GET, POST, PUT, PATCH, DELETE
}

enum APIError: LocalizedError {
    case invalidResponse
    case unauthorized
    case forbidden
    case notFound
    case validation(String)
    case server(Int, String)
    case network(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "Gecersiz sunucu yaniti"
        case .unauthorized: return "Oturum suresi doldu"
        case .forbidden: return "Bu islem icin yetkiniz yok"
        case .notFound: return "Kaynak bulunamadi"
        case .validation(let msg): return msg
        case .server(_, let msg): return msg
        case .network(let error): return error.localizedDescription
        }
    }
}

struct SSEEvent: Codable {
    let type: String      // "token" | "tool_start" | "tool_done" | "done" | "error"
    let content: String?
    let toolName: String?
    let conversationId: String?

    enum CodingKeys: String, CodingKey {
        case type, content
        case toolName = "tool_name"
        case conversationId = "conversation_id"
    }
}
```

### 6.2 AuthManager
```swift
@Observable
final class AuthManager {
    static let shared = AuthManager()

    private(set) var isAuthenticated = false
    private(set) var currentUser: AuthUser?
    private(set) var accessToken: String?
    private(set) var refreshTokenValue: String?
    private var tokenExpiresAt: Date?

    private let supabaseURL: String
    private let supabaseAnonKey: String
    private let keychain = KeychainAccess.Keychain(service: "com.marketpulse.ios")

    init() {
        #if DEBUG
        self.supabaseURL = "https://xxgvnqnykkbkhjdnizge.supabase.co"
        #else
        self.supabaseURL = Bundle.main.infoDictionary?["SUPABASE_URL"] as? String ?? ""
        #endif
        self.supabaseAnonKey = Bundle.main.infoDictionary?["SUPABASE_ANON_KEY"] as? String ?? ""

        // Keychain'den token restore
        restoreSession()
    }

    func signIn(email: String, password: String) async throws {
        let url = URL(string: "\(supabaseURL)/auth/v1/token?grant_type=password")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(supabaseAnonKey, forHTTPHeaderField: "apikey")

        let body = ["email": email, "password": password]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw AuthError.invalidCredentials
        }

        let authResponse = try JSONDecoder().decode(AuthResponse.self, from: data)
        saveTokens(authResponse)
    }

    func signUp(email: String, password: String, fullName: String?) async throws {
        let url = URL(string: "\(supabaseURL)/auth/v1/signup")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(supabaseAnonKey, forHTTPHeaderField: "apikey")

        var body: [String: Any] = ["email": email, "password": password]
        if let fullName = fullName {
            body["data"] = ["full_name": fullName]
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw AuthError.signUpFailed
        }

        let authResponse = try JSONDecoder().decode(AuthResponse.self, from: data)
        saveTokens(authResponse)
    }

    func refreshToken() async throws {
        guard let refreshToken = refreshTokenValue else { throw AuthError.noRefreshToken }

        let url = URL(string: "\(supabaseURL)/auth/v1/token?grant_type=refresh_token")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(supabaseAnonKey, forHTTPHeaderField: "apikey")

        let body = ["refresh_token": refreshToken]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            signOut()
            throw AuthError.refreshFailed
        }

        let authResponse = try JSONDecoder().decode(AuthResponse.self, from: data)
        saveTokens(authResponse)
    }

    func signOut() {
        accessToken = nil
        refreshTokenValue = nil
        currentUser = nil
        isAuthenticated = false
        tokenExpiresAt = nil

        try? keychain.remove("access_token")
        try? keychain.remove("refresh_token")
    }

    // MARK: - Private

    private func saveTokens(_ response: AuthResponse) {
        accessToken = response.accessToken
        refreshTokenValue = response.refreshToken
        currentUser = response.user
        isAuthenticated = true
        tokenExpiresAt = Date().addingTimeInterval(TimeInterval(response.expiresIn))

        keychain["access_token"] = response.accessToken
        keychain["refresh_token"] = response.refreshToken
    }

    private func restoreSession() {
        if let token = keychain["access_token"], let refresh = keychain["refresh_token"] {
            accessToken = token
            refreshTokenValue = refresh
            isAuthenticated = true
            // Token gecerliligini ilk API call'da kontrol edecegiz
        }
    }
}

enum AuthError: LocalizedError {
    case invalidCredentials
    case signUpFailed
    case noRefreshToken
    case refreshFailed

    var errorDescription: String? {
        switch self {
        case .invalidCredentials: return "Gecersiz email veya sifre"
        case .signUpFailed: return "Kayit basarisiz"
        case .noRefreshToken: return "Oturum suresi doldu, tekrar giris yapin"
        case .refreshFailed: return "Oturum yenilenemedi"
        }
    }
}
```

---

## 7. Design System

### 7.1 Renkler
```swift
extension Color {
    // Primary
    static let mpPrimary = Color(hex: "6366F1")       // Indigo
    static let mpPrimaryLight = Color(hex: "818CF8")

    // Status
    static let mpSuccess = Color(hex: "10B981")         // Yesil
    static let mpDanger = Color(hex: "EF4444")          // Kirmizi
    static let mpWarning = Color(hex: "F59E0B")         // Sari
    static let mpInfo = Color(hex: "3B82F6")            // Mavi

    // Background
    static let mpBackground = Color(.systemGroupedBackground)
    static let mpCardBackground = Color(.secondarySystemGroupedBackground)

    // Text
    static let mpTextPrimary = Color(.label)
    static let mpTextSecondary = Color(.secondaryLabel)

    // Platform
    static let mpHepsiburada = Color(hex: "FF6000")     // HB turuncu
    static let mpTrendyol = Color(hex: "F27A1A")        // TY turuncu
}
```

### 7.2 Typography
```swift
extension Font {
    static let mpTitle = Font.system(.title2, weight: .bold)
    static let mpHeadline = Font.system(.headline, weight: .semibold)
    static let mpBody = Font.system(.body)
    static let mpCaption = Font.system(.caption, weight: .medium)
    static let mpPrice = Font.system(.title3, design: .rounded, weight: .bold)
}
```

### 7.3 Ortak Bilesenler
```swift
// Platform Segmented Control
struct PlatformPicker: View {
    @Binding var selection: String
    let platforms = [("hepsiburada", "Hepsiburada"), ("trendyol", "Trendyol")]

    var body: some View {
        Picker("Platform", selection: $selection) {
            ForEach(platforms, id: \.0) { value, label in
                Text(label).tag(value)
            }
        }
        .pickerStyle(.segmented)
    }
}

// Price Label
struct PriceLabel: View {
    let price: Double
    let currency: String = "TRY"

    var body: some View {
        Text(price.formatted(.currency(code: currency)))
            .font(.mpPrice)
    }
}

// Seller Avatar (logo fallback)
struct SellerAvatar: View {
    let logoURL: String?
    let name: String
    let size: CGFloat = 40

    var body: some View {
        if let url = logoURL, let imageURL = URL(string: url) {
            AsyncImage(url: imageURL) { image in
                image.resizable().scaledToFit()
            } placeholder: {
                initialsView
            }
            .frame(width: size, height: size)
            .clipShape(Circle())
        } else {
            initialsView
        }
    }

    private var initialsView: some View {
        Circle()
            .fill(Color.mpPrimary.opacity(0.15))
            .frame(width: size, height: size)
            .overlay(
                Text(String(name.prefix(2)).uppercased())
                    .font(.mpCaption)
                    .foregroundColor(.mpPrimary)
            )
    }
}

// Empty State
struct EmptyStateView: View {
    let icon: String
    let title: String
    let message: String
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundColor(.mpTextSecondary)
            Text(title).font(.mpHeadline)
            Text(message)
                .font(.mpBody)
                .foregroundColor(.mpTextSecondary)
                .multilineTextAlignment(.center)
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .buttonStyle(.borderedProminent)
            }
        }
        .padding(40)
    }
}
```

### 7.4 Para Formatlama
```swift
extension Double {
    var tryFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "TRY"
        formatter.locale = Locale(identifier: "tr_TR")
        return formatter.string(from: NSNumber(value: self)) ?? "₺\(self)"
    }

    var percentFormatted: String {
        String(format: "%+.1f%%", self)
    }
}
```

---

## 8. Offline & Caching Stratejisi

### 8.1 URLCache
```swift
// Default URLCache (50MB memory, 200MB disk)
URLCache.shared = URLCache(
    memoryCapacity: 50 * 1024 * 1024,
    diskCapacity: 200 * 1024 * 1024,
    diskPath: "marketpulse_cache"
)
```

### 8.2 Veri Onbellekleme Kurallari

| Veri | Cache Suresi | Strateji |
|------|-------------|----------|
| Dashboard Summary | 5 dk | Stale-while-revalidate |
| Product List | 2 dk | Invalidate on mutation |
| Seller List | 5 dk | Stale-while-revalidate |
| Brand List | 30 dk | Long-lived cache |
| Category Tree | 30 dk | Long-lived cache |
| Price History | 10 dk | On-demand |
| Fetch Task Status | 0 (no cache) | Real-time polling |

### 8.3 Offline Gosterim
- Son basarili API yanitini cache'le
- Network hatasi → cache'den goster + banner: "Cevrimdisi - Son veriler gosteriliyor"
- Pull-to-refresh → network yeniden dene

---

## 9. Push Notifications (Gelecek)

### 9.1 APNs Entegrasyonu
```swift
// AppDelegate'de token kayit
func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
    Task {
        try await APIClient.shared.request(.POST, path: "notifications/register-device", body: [
            "device_token": token,
            "platform": "ios"
        ])
    }
}
```

### 9.2 Bildirim Turleri
| Tur | Aciklama | Aksiyon |
|-----|----------|---------|
| `price_alert` | Fiyat esik ihlali | Urun detayina git |
| `campaign_alert` | Yeni kampanya | Urun detayina git |
| `buybox_lost` | Buybox kaybi | Satici listesine git |
| `fetch_complete` | Tarama tamamlandi | Product listesine git |
| `daily_digest` | Gunluk ozet | Dashboard'a git |

### 9.3 Backend Gereksinimi (Henuz Yok)
Bu endpoint'ler iOS launch oncesi backend'e eklenmeli:
- `POST /api/notifications/register-device` — APNs token kayit
- `DELETE /api/notifications/unregister-device` — Token silme
- `GET /api/notifications/preferences` — Bildirim tercihleri
- `PUT /api/notifications/preferences` — Tercih guncelleme

---

## 10. Abonelik & Plan Limitleri

### 10.1 Plan Tierleri

| Ozellik | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| Aylik Ucret | 0 TL | 299 TL | 899 TL | Ozel |
| Max SKU | 10 | 200 | 1,000 | Sinirsiz |
| Platform | 1 | 2 | Tum | Tum |
| Gunluk Tarama | 1x Manuel | 2x Otomatik | 4x Otomatik | 24x |
| Gecmis (gun) | 7 | 30 | 90 | Sinirsiz |
| Email Alarm | - | 10/gun | Sinirsiz | Sinirsiz |
| CSV Export | - | Var | Var | Var |
| Kategori Analizi | - | - | Var | Var |
| API Erisim | - | - | - | Var |

### 10.2 iOS'ta Plan Yonetimi
- Plan gosterimi: `GET /api/billing/subscription`
- Plan degistirme: `POST /api/billing/checkout` → Safari'de Stripe Checkout acilir
- Mevcut plan yonetimi: `POST /api/billing/portal` → Safari'de Stripe Portal
- **Not:** In-app purchase kullanilmiyor. Stripe web-based checkout tercih ediliyor.

---

## 11. Xcode Proje Yapisi

```
MarketPulse/
├── MarketPulseApp.swift                    # @main App entry
├── Info.plist
├── Assets.xcassets/
│
├── Core/
│   ├── Network/
│   │   ├── APIClient.swift                 # URLSession actor
│   │   ├── APIError.swift                  # Error types
│   │   ├── Endpoint.swift                  # API endpoint enum
│   │   └── SSEClient.swift                 # Server-Sent Events
│   ├── Auth/
│   │   ├── AuthManager.swift               # Supabase JWT auth
│   │   └── KeychainManager.swift           # Token storage
│   ├── Extensions/
│   │   ├── Color+MarketPulse.swift
│   │   ├── Font+MarketPulse.swift
│   │   ├── Double+Formatting.swift
│   │   └── View+Loading.swift
│   └── Utilities/
│       ├── CacheManager.swift
│       └── Debouncer.swift
│
├── Models/
│   ├── Auth/
│   │   ├── AuthResponse.swift
│   │   └── AuthUser.swift
│   ├── Dashboard/
│   │   ├── DashboardSummary.swift
│   │   ├── PriceMover.swift
│   │   └── ProfitabilityOverview.swift
│   ├── PriceMonitor/
│   │   ├── MonitoredProduct.swift
│   │   ├── SellerSnapshot.swift
│   │   ├── FetchTask.swift
│   │   └── PriceHistory.swift
│   ├── Seller/
│   │   ├── SellerInfo.swift
│   │   └── SellerProducts.swift
│   ├── Category/
│   │   ├── CategoryTreeNode.swift
│   │   ├── CategoryProduct.swift
│   │   └── CategorySession.swift
│   ├── Chat/
│   │   ├── ChatMessage.swift
│   │   ├── ChatConversation.swift
│   │   └── SSEEvent.swift
│   └── Settings/
│       ├── Subscription.swift
│       └── ScheduledTask.swift
│
├── Repositories/
│   ├── DashboardRepository.swift
│   ├── PriceMonitorRepository.swift
│   ├── SellerRepository.swift
│   ├── CategoryRepository.swift
│   ├── ChatRepository.swift
│   ├── SettingsRepository.swift
│   └── Protocols/
│       ├── DashboardRepositoryProtocol.swift
│       ├── PriceMonitorRepositoryProtocol.swift
│       └── ...
│
├── ViewModels/
│   ├── AuthViewModel.swift
│   ├── DashboardViewModel.swift
│   ├── PriceMonitorListViewModel.swift
│   ├── PriceMonitorDetailViewModel.swift
│   ├── SellerListViewModel.swift
│   ├── SellerDetailViewModel.swift
│   ├── CategoryExplorerViewModel.swift
│   ├── SettingsViewModel.swift
│   └── AIChatViewModel.swift
│
├── Views/
│   ├── MainTabView.swift
│   ├── Auth/
│   │   ├── LoginView.swift
│   │   ├── RegisterView.swift
│   │   └── OnboardingView.swift
│   ├── Dashboard/
│   │   ├── DashboardView.swift
│   │   ├── SKUOverviewCard.swift
│   │   ├── AlertsCard.swift
│   │   ├── PriceMoversCard.swift
│   │   └── ProfitabilityCard.swift
│   ├── PriceMonitor/
│   │   ├── PriceMonitorListView.swift
│   │   ├── PriceMonitorDetailView.swift
│   │   ├── PriceMonitorFilters.swift
│   │   ├── ProductRowView.swift
│   │   ├── SellerRowView.swift
│   │   ├── FetchProgressView.swift
│   │   ├── ImportSheet.swift
│   │   ├── ThresholdEditSheet.swift
│   │   └── PriceChartView.swift
│   ├── Sellers/
│   │   ├── SellerListView.swift
│   │   ├── SellerDetailView.swift
│   │   └── SellerCard.swift
│   ├── Category/
│   │   ├── CategoryExplorerView.swift
│   │   ├── CategoryTreeView.swift
│   │   ├── CategoryProductGrid.swift
│   │   ├── CategoryFiltersSheet.swift
│   │   └── ScrapeProgressView.swift
│   ├── Settings/
│   │   ├── SettingsView.swift
│   │   ├── SubscriptionSection.swift
│   │   ├── NotificationSection.swift
│   │   └── ScheduledTasksSection.swift
│   ├── Chat/
│   │   ├── AIChatView.swift
│   │   ├── AIChatFloatingButton.swift
│   │   ├── ChatMessageBubble.swift
│   │   └── ChatSuggestions.swift
│   └── Shared/
│       ├── PlatformPicker.swift
│       ├── PriceLabel.swift
│       ├── SellerAvatar.swift
│       ├── EmptyStateView.swift
│       ├── LoadingView.swift
│       ├── ErrorView.swift
│       └── ConfirmationDialog.swift
│
├── MarketPulseTests/
│   ├── ViewModelTests/
│   ├── RepositoryTests/
│   └── Mocks/
│
└── MarketPulseUITests/
    └── ...
```

---

## 12. Implementasyon Fazlari

### Faz 1: Temel Altyapi (Hafta 1-2)
- [ ] Xcode projesi olustur (iOS 17+, Swift 6)
- [ ] Core/Network katmani: APIClient actor, error handling
- [ ] Core/Auth: AuthManager, Keychain, Supabase login/register
- [ ] Auth ekranlari: LoginView, RegisterView
- [ ] MainTabView iskelet (5 tab, bos icerik)
- [ ] Design system: renkler, fontlar, ortak bilesenler
- [ ] Navigation stack yapisi

### Faz 2: Dashboard + Price Monitor (Hafta 3-4)
- [ ] Dashboard 3 endpoint entegrasyonu
- [ ] Dashboard kartlari: SKU, Alerts, Price Movers, Profitability
- [ ] Price Monitor liste ekrani (filtreler, arama, pagination)
- [ ] Price Monitor detay ekrani (satici listesi)
- [ ] Fiyat gecmisi grafigi (Swift Charts)
- [ ] Fetch task baslat/durdur + polling
- [ ] Import/Export islevleri
- [ ] Pull-to-refresh

### Faz 3: Sellers + Category (Hafta 5-6)
- [ ] Satici listesi ekrani
- [ ] Satici detay ekrani (urunleri)
- [ ] CSV export (Share Sheet)
- [ ] Category Explorer: Platform + mod secimi
- [ ] My Products: filtreler, kategori agaci, urun listesi
- [ ] Category Page: scrape baslat, urun listesi, filtreler
- [ ] Detail fetch + polling

### Faz 4: AI Chat + Settings (Hafta 7-8)
- [ ] AI Chat: SSE streaming, mesaj listesi
- [ ] Context-aware oneriler (aktif ekrana gore)
- [ ] Conversation yonetimi (listele, sil)
- [ ] Settings: Profil, abonelik bilgisi
- [ ] Stripe checkout (Safari redirect)
- [ ] Zamanlanmis gorevler CRUD
- [ ] Onboarding akisi (4 adim)

### Faz 5: Polish + Launch (Hafta 9-10)
- [ ] Offline cache + error handling
- [ ] Skeleton loading animasyonlari
- [ ] Haptic feedback
- [ ] VoiceOver accessibility
- [ ] Dark mode tam destek
- [ ] Performance optimizasyonu (lazy loading, image cache)
- [ ] TestFlight beta
- [ ] App Store submission

---

## 13. Endpoint Ozet Tablosu

### Supabase Auth (3 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| POST | `/auth/v1/token?grant_type=password` | Login |
| POST | `/auth/v1/signup` | Register |
| POST | `/auth/v1/token?grant_type=refresh_token` | Token yenileme |

### Dashboard (3 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| GET | `/api/dashboard/summary` | Ozet veriler |
| GET | `/api/dashboard/price-movers` | Fiyat hareketleri |
| GET | `/api/dashboard/profitability-overview` | Karlilik ozeti |

### Price Monitor (14 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| GET | `/api/price-monitor/products` | Urun listesi |
| POST | `/api/price-monitor/products` | Toplu urun ekle |
| GET | `/api/price-monitor/products/{id}` | Urun detay + saticilar |
| PUT | `/api/price-monitor/products/{id}` | Urun guncelle |
| DELETE | `/api/price-monitor/products/{id}` | Urun sil |
| DELETE | `/api/price-monitor/products/bulk/all` | Tumu sil |
| DELETE | `/api/price-monitor/products/bulk/inactive` | Inaktifleri sil |
| POST | `/api/price-monitor/products/import` | CSV/XLSX import |
| POST | `/api/price-monitor/fetch` | Fetch gorevi baslat |
| GET | `/api/price-monitor/fetch/{task_id}` | Gorev durumu (polling) |
| POST | `/api/price-monitor/fetch/{task_id}/stop` | Gorevi durdur |
| POST | `/api/price-monitor/fetch-single/{product_id}` | Tek urun fetch |
| GET | `/api/price-monitor/brands` | Marka listesi |
| GET | `/api/price-monitor/export` | JSON export |
| GET | `/api/price-monitor/last-inactive` | Son inaktif SKU'lar |
| GET | `/api/price-monitor/products/{id}/price-history` | Fiyat gecmisi |

### Sellers (3 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| GET | `/api/sellers` | Satici listesi |
| GET | `/api/sellers/{merchant_id}/products` | Satici urunleri |
| GET | `/api/sellers/{merchant_id}/export` | CSV export |

### Category Explorer (10 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| POST | `/api/category-explorer/scrape` | Kategori tara |
| GET | `/api/category-explorer/sessions` | Oturum listesi |
| GET | `/api/category-explorer/sessions/{id}` | Oturum detay |
| DELETE | `/api/category-explorer/sessions/{id}` | Oturum sil |
| POST | `/api/category-explorer/fetch-details` | Detay bilgi cek |
| GET | `/api/category-explorer/fetch-status/{session_id}` | Fetch durumu |
| GET | `/api/category-explorer/products-by-category` | Urunler (filtreli) |
| GET | `/api/category-explorer/category-filters` | Filtre secenekleri |
| DELETE | `/api/category-explorer/products/{id}` | Urun sil |
| POST | `/api/category-explorer/products/bulk-delete` | Toplu sil |

### Store Products (10 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| GET | `/api/store-products` | Urun listesi |
| GET | `/api/store-products/filters` | Filtre secenekleri |
| GET | `/api/store-products/category-tree` | Kategori agaci |
| GET | `/api/store-products/stats` | Istatistikler |
| GET | `/api/store-products/{id}` | Urun detay |
| POST | `/api/store-products/scrape-from-pm` | PM'den tara |
| GET | `/api/store-products/scrape-status/{job_id}` | Tarama durumu |
| POST | `/api/store-products/save-from-scrape/{job_id}` | Sonuclari kaydet |
| DELETE | `/api/store-products/{id}` | Urun sil |
| DELETE | `/api/store-products/all` | Tumu sil |

### AI Chat (5 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| POST | `/api/ai/chat/stream` | SSE streaming chat |
| POST | `/api/ai/chat` | Non-streaming chat |
| GET | `/api/ai/conversations` | Sohbet listesi |
| GET | `/api/ai/conversations/{id}/messages` | Mesajlar |
| DELETE | `/api/ai/conversations/{id}` | Sohbet sil |

### Billing (4 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| GET | `/api/billing/subscription` | Abonelik bilgisi |
| GET | `/api/billing/plans` | Plan listesi |
| POST | `/api/billing/checkout` | Stripe checkout |
| POST | `/api/billing/portal` | Stripe portal |

### Scheduler (4 endpoint)
| Method | Path | Kullanim |
|--------|------|----------|
| GET | `/api/scheduler/tasks` | Gorev listesi |
| POST | `/api/scheduler/tasks` | Yeni gorev |
| PUT | `/api/scheduler/tasks/{id}` | Gorev guncelle |
| DELETE | `/api/scheduler/tasks/{id}` | Gorev sil |

**Toplam: 56+ endpoint** (3 Supabase Auth + 53+ Backend API)

---

## 14. Backend Eksik Endpoint'ler (iOS Oncesi Gerekli)

| Endpoint | Aciklama | Oncelik |
|----------|----------|---------|
| `POST /api/notifications/register-device` | APNs push token kayit | Yuksek |
| `DELETE /api/notifications/unregister-device` | Token silme (logout) | Yuksek |
| `GET /api/notifications/preferences` | Bildirim tercihleri | Orta |
| `PUT /api/notifications/preferences` | Tercih guncelleme | Orta |
| `GET /api/user/onboarding-status` | Onboarding tamamlandi mi | Dusuk |
| `PUT /api/user/onboarding-status` | Onboarding durumu kaydet | Dusuk |
| `GET /api/mobile/version-check` | Minimum app versiyonu | Opsiyonel |

---

## 15. LLM Agent Icin Prompt Sablonlari

iOS gelistirme sirasinda Claude Agent'a verilebilecek prompt ornekleri:

### Yeni Ekran Olusturma
```
MARKETPULSE_IOS_APP_SPEC.md dokumandaki [EkranAdi] bolumune gore:
1. ViewModel olustur (repository pattern, @Observable)
2. SwiftUI View olustur (dokumandaki wireframe'e uygun)
3. Repository metotlarini ekle (APIClient kullanarak)
4. Navigation entegrasyonunu yap
Dokumandaki endpoint tablosunu referans al.
```

### Model Olusturma
```
IOS_SCREENS_AND_API_REFERENCE.md dokümanindaki [endpoint] response formatina gore:
1. Swift Codable struct olustur
2. CodingKeys ekle (snake_case → camelCase)
3. Identifiable protocol'unu implement et
4. Opsiyonel alanlari dogru isaretle
```

### API Entegrasyonu
```
IOS_BACKEND_REQUIREMENTS.md dokümanindaki [endpoint] bolumune gore:
1. Repository protocol'une metot ekle
2. Concrete implementation'da APIClient.request kullan
3. Error handling ekle
4. ViewModel'den cagir ve state'i guncelle
```

---

## 16. Onemli Teknik Notlar

### 16.1 Platform Degerleri
Her zaman lowercase string: `"hepsiburada"` veya `"trendyol"`. API'ye gonderirken ve UI'da gosterirken bu convention'a uy.

### 16.2 Para Birimi
Tum fiyatlar TRY (Turk Lirasi). Backend `Numeric(10,2)` tipinde doner. iOS'ta `Double` olarak isle, gosterirken `NumberFormatter` ile `tr_TR` locale kullan.

### 16.3 Tarih Formatlari
Backend ISO 8601 formatinda tarih doner: `"2026-03-01T14:30:00"`. iOS'ta `ISO8601DateFormatter` veya custom `DateFormatter` kullan.

### 16.4 UUID Formatı
Tum ID'ler UUID string: `"550e8400-e29b-41d4-a716-446655440000"`. Swift'te `String` olarak tut (UUID type yerine), cunku backend string olarak doner.

### 16.5 Pagination Farklari
- **Price Monitor:** offset-based → `limit=100&offset=0` → sonraki sayfa: `offset=100`
- **Category Explorer:** page-based → `page=1&page_size=50` → sonraki sayfa: `page=2`
- **Sellers:** Tek sayfa → `limit=200&offset=0` (genelde yeterli)

### 16.6 Polling Sureleri
- Fetch task status: **2 saniye** (Price Monitor)
- Category detail fetch: **3 saniye**
- Terminal stateler: `"completed"`, `"failed"`, `"stopped"` → polling'i durdur

### 16.7 Debounce
- Arama input'u: **400ms** debounce sonrasi API cagir
- Swift'te `Task` + `try await Task.sleep(nanoseconds:)` pattern veya Combine `debounce` kullan

### 16.8 CORS
iOS native URLSession CORS'a tabi degildir. Backend'de CORS degisikligi gerekmez.

### 16.9 Image Loading
- `AsyncImage` kullan (SwiftUI native)
- Placeholder: `ProgressView()` veya skeleton
- Error: SF Symbol placeholder (`photo` veya `shippingbox`)
- Cache: URLSession'in default cache'i yeterli, gerekirse Kingfisher ekle
