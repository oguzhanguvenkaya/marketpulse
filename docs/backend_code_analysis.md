# Backend Kod Analizi Raporu

Bu rapor, pazaryeri veri analiz platformunun backend servislerinin detaylı analizini içerir.

---

## 1. proxy_providers.py - Proxy Yönetim Sistemi

### Genel Amaç
Farklı proxy sağlayıcılarını yönetmek, otomatik fallback mantığı sağlamak ve debug logging yapmak.

---

### 1.1 ProxyProvider (Abstract Base Class)

**Amaç:** Tüm proxy sağlayıcıları için şablon tanımlar.

| Metod | Girdi | Çıktı | Açıklama |
|-------|-------|-------|----------|
| `get_proxy_config(premium)` | `premium: bool` | `Dict[str, str]` veya `None` | Proxy bağlantı ayarlarını döner |
| `is_available()` | - | `bool` | Provider'ın kullanılabilir olup olmadığını kontrol eder |
| `get_description()` | - | `str` | Provider'ın açıklamasını döner |

---

### 1.2 ScraperAPIProvider

**Amaç:** ScraperAPI proxy servisini yönetir (birincil, ucuz seçenek).

| Metod | Girdi | Çıktı | Açıklama |
|-------|-------|-------|----------|
| `get_proxy_config(premium)` | `premium: bool = False` | `Dict` veya `None` | ScraperAPI proxy URL, username, password döner |
| `is_available()` | - | `bool` | `SCRAPER_API_KEY` environment variable var mı kontrol |

**Proxy Config Çıktısı:**
```python
{
    "server": "http://proxy-server.scraperapi.com:8001",
    "username": "scraperapi.country_code=tr...",
    "password": "<API_KEY>"
}
```

---

### 1.3 BrightDataProvider

**Amaç:** Bright Data residential proxy servisini yönetir (fallback, premium).

| Metod | Girdi | Çıktı | Açıklama |
|-------|-------|-------|----------|
| `get_proxy_config(premium)` | `premium: bool = False` | `Dict` veya `None` | Bright Data proxy ayarlarını döner |
| `is_available()` | - | `bool` | Bright Data credentials var mı kontrol |

---

### 1.4 DirectProvider

**Amaç:** Proxy olmadan doğrudan bağlantı sağlar (son çare).

| Metod | Girdi | Çıktı | Açıklama |
|-------|-------|-------|----------|
| `get_proxy_config(premium)` | - | `None` | Her zaman None döner (proxy yok) |
| `is_available()` | - | `True` | Her zaman kullanılabilir |

---

### 1.5 ProxyManager

**Amaç:** Tüm provider'ları yönetir, otomatik seçim ve fallback yapar.

| Metod | Girdi | Çıktı | Açıklama |
|-------|-------|-------|----------|
| `get_provider(name)` | `name: str` | `ProxyProvider` | İsme göre provider döner |
| `get_available_providers()` | - | `List[Dict]` | Tüm provider'ları ve durumlarını listeler |
| `get_primary_provider()` | - | `ProxyProvider` | Ayarlara göre birincil provider'ı döner |
| `get_fallback_provider(current)` | `current: str` | `ProxyProvider` veya `None` | Mevcut provider başarısız olursa bir sonrakini döner |
| `get_proxy_config(provider_name, premium)` | `provider_name: str`, `premium: bool` | `Dict` veya `None` | Belirtilen provider'ın config'ini döner |

**Fallback Zinciri:**
```
scraperapi → brightdata → direct
```

---

### 1.6 DebugLogger

**Amaç:** Scraping isteklerini loglar ve hata durumunda HTML kaydeder.

| Metod | Girdi | Çıktı | Açıklama |
|-------|-------|-------|----------|
| `log_request(url, provider, status, message)` | `url: str`, `provider: str`, `status: int`, `message: str` | - | İsteği loglar ve dosyaya yazar |
| `save_debug_html(url, html_content, status, provider)` | `url: str`, `html: str`, `status: int`, `provider: str` | `filepath: str` | Hata HTML'ini `/tmp/scraping_debug/` altına kaydeder |
| `log_error(url, provider, error)` | `url: str`, `provider: str`, `error: Exception` | - | Hatayı error log dosyasına yazar |

---

## 2. scraping.py - Ana Scraping Servisi

### Genel Amaç
Hepsiburada'dan ürün verilerini çekmek, parse etmek ve yapılandırılmış veri olarak döndürmek.

---

### 2.1 ScrapingService.__init__

**Amaç:** Servis instance'ını başlatır.

**Özellikler:**
- `browser`: Playwright browser instance
- `playwright`: Playwright manager
- `context`: Browser context (cookies, headers)
- `current_provider`: Aktif proxy provider
- `current_provider_name`: Provider adı string

---

### 2.2 Browser Yönetimi

| Metod | Girdi | Çıktı | Açıklama |
|-------|-------|-------|----------|
| `init_browser(provider_name, premium)` | `provider_name: str = None`, `premium: bool = False` | `Browser` | Playwright browser başlatır, proxy config uygular |
| `close_browser()` | - | - | Browser, context ve playwright'ı kapatır |
| `reinit_with_fallback()` | - | `bool` | Mevcut browser'ı kapatır, fallback provider ile yeniden başlatır |

**Browser Context Ayarları:**
```python
{
    'viewport': {'width': 1920, 'height': 1080},
    'user_agent': 'Chrome/120.0.0.0',
    'locale': 'tr-TR',
    'timezone_id': 'Europe/Istanbul',
    'extra_http_headers': {...}  # Anti-detection headers
}
```

---

### 2.3 HTTP İstek Metodları

#### `_fetch_with_scraperapi_proxy(url, session_number, render_js, wait_for_selector)`

**Amaç:** ScraperAPI PROXY PORT metodu ile sayfa çeker.

| Parametre | Tip | Varsayılan | Açıklama |
|-----------|-----|------------|----------|
| `url` | `str` | - | Çekilecek URL |
| `session_number` | `int` | `1` | Sticky session için session ID |
| `render_js` | `bool` | `False` | JavaScript render etsin mi |
| `wait_for_selector` | `str` | `None` | Beklenecek CSS selector |

**Çıktı:** `str` (HTML içerik) veya `None` (başarısız)

**Username Format:**
```
scraperapi.render=true.country_code=tr.device_type=desktop.max_cost=200.session_number=1234
```

---

#### `_fetch_with_scraperapi(url, render, premium)`

**Amaç:** ScraperAPI HTTP API metodu ile sayfa çeker (kullanılmıyor, proxy port tercih ediliyor).

| Parametre | Tip | Varsayılan | Açıklama |
|-----------|-----|------------|----------|
| `url` | `str` | - | Çekilecek URL |
| `render` | `bool` | `True` | JavaScript render |
| `premium` | `bool` | `False` | Premium proxy kullan |

**Çıktı:** `str` (HTML) veya `None`

---

### 2.4 Arama Sayfası İşleme

#### `scrape_hepsiburada_search(keyword, max_products)`

**Amaç:** Ana arama fonksiyonu. Keyword'e göre ürünleri arar ve scrape eder.

| Parametre | Tip | Varsayılan | Açıklama |
|-----------|-----|------------|----------|
| `keyword` | `str` | - | Arama kelimesi |
| `max_products` | `int` | `8` | Maksimum ürün sayısı |

**Çıktı:**
```python
{
    'products': [
        {
            'platform': 'hepsiburada',
            'external_id': 'HBC00004KHI7D',
            'name': 'Ürün Adı',
            'url': 'https://...',
            'price': 607.6,
            'rating': 4.8,
            'brand': 'Nasiol',
            'seller_name': 'Satıcı',
            'discounted_price': None,
            'coupons': [],
            'campaigns': [],
            'other_sellers': [...],
            'reviews': [...],
            ...
        }
    ],
    'sponsored_brands': [
        {
            'seller_name': 'TULPAR KİMYA',
            'seller_id': '123',
            'position': 1,
            'products': [...]
        }
    ]
}
```

---

#### `_get_product_urls_via_http_api(keyword, max_products)`

**Amaç:** Arama sayfasından ürün URL'lerini çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `keyword` | `str` | Arama kelimesi |
| `max_products` | `int` | Maksimum URL sayısı |

**Çıktı:**
```python
{
    'urls': ['https://...', ...],           # Ürün URL listesi
    'sponsored_brands': [...],               # Marka reklamları
    'sponsored_product_urls': {'url1', ...}  # Sponsorlu ürün URL'leri
}
```

---

#### `_extract_product_urls_from_soup(soup, max_products)`

**Amaç:** BeautifulSoup objesiinden ürün URL'lerini çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `soup` | `BeautifulSoup` | Parse edilmiş HTML |
| `max_products` | `int` | Maksimum URL |

**Çıktı:** `List[str]` - Temizlenmiş ürün URL listesi

**CSS Selector Önceliği:**
1. `article[class*="productCard-module_article"]`
2. `a[class*="productCardLink"]`
3. `ul[class*="productListContent"]`
4. Fallback: `a[href*="-p-"]`

---

### 2.5 Ürün Detay Sayfası İşleme

#### `scrape_product_detail_page(url)`

**Amaç:** Ürün detay sayfasını scrape eder, ana koordinatör fonksiyon.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `url` | `str` | Ürün URL'i |

**Çıktı:** `Dict[str, Any]` - Tam ürün verisi veya `None`

**Akış:**
```
1. ScraperAPI render_js=True dene
   ↓ (500 hatası)
2. ScraperAPI standart dene
   ↓ (başarılı, discounted_price yok)
3. Playwright fallback ile dene
   ↓
4. Sonuçları birleştir
```

---

#### `_scrape_product_via_http_api(url, session_number)`

**Amaç:** ScraperAPI ile ürün detay sayfasını çeker ve parse eder.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `url` | `str` | Ürün URL'i |
| `session_number` | `int` | Session ID |

**Çıktı:** Tam `product_data` dict veya `None`

**Parse Sırası:**
1. `utagData` JavaScript objesi → fiyat, marka, kategori
2. `JSON-LD` şeması → rating, açıklama, resim
3. HTML elementleri → indirimli fiyat, kuponlar, stok

---

#### `_scrape_product_via_playwright(url)`

**Amaç:** Playwright ile JS-rendered içerik çeker (fallback).

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `url` | `str` | Ürün URL'i |

**Çıktı:** `html_data` dict (sadece discounted_price, coupons, campaigns, stock)

**Önemli:** Bu metod sadece HTML verisi döner, tam product_data değil. Ana veriye merge edilir.

---

### 2.6 Veri Çıkarma Metodları

#### `_extract_utag_data(html_content)`

**Amaç:** Sayfadaki `utagData` JavaScript objesini çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `html_content` | `str` | Ham HTML |

**Çıktı:** `Dict` - utagData objesi veya `None`

**Çıkarma Stratejisi:**
```
1. Regex: const utagData = {...}; window.utagData
2. Regex: const utagData = {...};
3. Brace-counting algoritması
```

---

#### `_parse_utag_data(utag_data)`

**Amaç:** utagData'yı yapılandırılmış ürün verisine dönüştürür.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `utag_data` | `Dict` | utagData objesi |

**Çıktı:**
```python
{
    'name': 'Ürün Adı',
    'price': 607.6,
    'rating': 4.8,
    'reviews_count': 150,
    'brand': 'Nasiol',
    'seller_name': 'Satıcı',
    'seller_rating': 9.8,
    'sku': 'ABC123',
    'barcode': '8690...',
    'category_path': 'Otomobil > Aksesuar',
    'category_hierarchy': 'Otomobil|Aksesuar|Temizlik',
    'in_stock': True
}
```

---

#### `_extract_json_ld_data(soup)`

**Amaç:** JSON-LD structured data çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `soup` | `BeautifulSoup` | Parse edilmiş HTML |

**Çıktı:** `Dict` - JSON-LD verisi (Product type)

---

#### `_extract_html_data(soup)`

**Amaç:** HTML elementlerinden dinamik veri çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `soup` | `BeautifulSoup` | Parse edilmiş HTML |

**Çıktı:**
```python
{
    'discounted_price': 499.90,      # Sepete özel fiyat
    'coupons': [...],                 # Kupon listesi
    'campaigns': [...],               # Kampanya listesi
    'stock_count': 50,                # Stok adedi
    'origin_country': 'Türkiye',      # Menşei ülke
    'description': '...',             # Ürün açıklaması
    'image_url': 'https://...'        # Ürün resmi
}
```

**Discounted Price CSS Selectors (8 adet):**
```css
[class*="sepete"]
[class*="cartSpecial"]
[class*="campaignPrice"]
[class*="discountedPrice"]
[data-test-id*="discounted"]
.sf-price
.product-price
[class*="currentPrice"]
```

---

#### `_extract_other_sellers(soup)`

**Amaç:** Diğer satıcıları çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `soup` | `BeautifulSoup` | Parse edilmiş HTML |

**Çıktı:**
```python
[
    {
        'seller_name': 'DS Detailing Store',
        'seller_rating': 9.9,
        'price': 799.00
    }
]
```

---

#### `_extract_reviews(soup)`

**Amaç:** Ürün yorumlarını çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `soup` | `BeautifulSoup` | Parse edilmiş HTML |

**Çıktı:**
```python
[
    {
        'author': 'Ahmet Y.',
        'rating': 5,
        'review_text': 'Çok güzel ürün...',
        'review_date': '2024-01-15',
        'seller_name': 'Nasiol'
    }
]
```

---

### 2.7 Sponsorlu İçerik İşleme

#### `_extract_sponsored_brands_from_search(html)`

**Amaç:** Arama sayfasından marka reklamlarını çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `html` | `str` | Ham HTML |

**Çıktı:** `List[Dict]` - Marka reklam listesi

**Regex Pattern:**
```regex
"adInfo":"...".*?"merchantName":"...".*?"merchantId":"...".*?"price":...
```

---

#### `_extract_sponsored_products_from_search(soup)`

**Amaç:** Arama sonuçlarından sponsorlu ürünleri (Reklam badge'li) çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `soup` | `BeautifulSoup` | Parse edilmiş HTML |

**Tespit Kriteri:**
```python
'advertisement-module_adRoot' in li_str  # Sponsorlu ürün
```

---

#### `_extract_real_url_from_tracking(href)`

**Amaç:** Reklam tracking URL'inden gerçek ürün URL'ini çıkarır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `href` | `str` | adservice tracking URL |

**Örnek:**
```
Girdi:  https://adservice.hepsiburada.com/...?redirect=https%3A%2F%2Fwww.hepsiburada.com%2Furun-p-123
Çıktı:  https://www.hepsiburada.com/urun-p-123
```

---

### 2.8 Yardımcı Metodlar

| Metod | Girdi | Çıktı | Açıklama |
|-------|-------|-------|----------|
| `_extract_external_id(url)` | `url: str` | `str` | URL'den ürün ID çıkarır (`-p-` veya `-pm-` sonrası) |
| `_parse_float(value)` | `Any` | `float` veya `None` | Türkçe format desteğiyle sayı parse eder |
| `_parse_int(value)` | `Any` | `int` veya `None` | Integer parse eder |
| `_random_delay(min_ms, max_ms)` | `int`, `int` | - | Anti-detection için rastgele bekleme |
| `_simulate_human_behavior(page)` | `Page` | - | Mouse hareketi ve scroll simülasyonu |
| `_apply_anti_detection(page)` | `Page` | - | WebDriver detection bypass |

---

## 3. routes.py - API Endpoint'leri

### Genel Amaç
Frontend ile backend arasında iletişim sağlayan REST API endpoint'lerini tanımlar.

---

### 3.1 Request/Response Modelleri

| Model | Amaç | Önemli Alanlar |
|-------|------|----------------|
| `SearchRequest` | Arama isteği | `keyword`, `platform` |
| `AnalysisRequest` | AI analiz isteği | `product_ids`, `question` |
| `SearchTaskResponse` | Task durumu | `id`, `status`, `total_products` |
| `ProductResponse` | Ürün özeti | Tüm ürün alanları + son snapshot |
| `ProductDetailResponse` | Ürün detayı | + `other_sellers`, `reviews` |
| `SnapshotResponse` | Fiyat geçmişi | `price`, `rating`, `date` |

---

### 3.2 Arama Endpoint'leri

#### `POST /api/search`

**Amaç:** Yeni arama görevi başlatır.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `keyword` | `str` | Arama kelimesi |
| `platform` | `str` | Platform (default: hepsiburada) |

**Çıktı:** `SearchTaskResponse` - Task ID ve durumu

**Akış:**
1. `SearchTask` oluştur (status: pending)
2. Background task başlat (`run_scraping_background`)
3. Task ID döndür

---

#### `GET /api/search/{task_id}`

**Amaç:** Arama görevinin durumunu sorgular.

**Çıktı:** `SearchTaskResponse` - Güncel durum

---

#### `GET /api/tasks`

**Amaç:** Son aramaları listeler.

| Parametre | Tip | Varsayılan | Açıklama |
|-----------|-----|------------|----------|
| `limit` | `int` | `10` | Maksimum kayıt |

**Çıktı:** `List[SearchTaskResponse]`

---

#### `GET /api/search/{task_id}/sponsored-brands`

**Amaç:** Bir aramanın marka reklamlarını döner.

**Çıktı:**
```json
{
    "keyword": "oto şampuan",
    "sponsored_brands": [
        {"seller_name": "TULPAR KİMYA", "position": 1, "products": [...]}
    ]
}
```

---

### 3.3 Ürün Endpoint'leri

#### `GET /api/products`

**Amaç:** Ürün listesini döner.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `keyword` | `str` | İsimde arama |
| `platform` | `str` | Platform filtresi |
| `limit` | `int` | Maksimum kayıt (default: 50) |

**Çıktı:** `List[ProductResponse]` - Her ürün son snapshot ile

---

#### `GET /api/products/{product_id}`

**Amaç:** Ürün detayını döner.

**Çıktı:** `ProductDetailResponse` - Ürün + diğer satıcılar + yorumlar

---

#### `GET /api/products/{product_id}/snapshots`

**Amaç:** Ürün fiyat/rating geçmişini döner.

| Parametre | Tip | Varsayılan | Açıklama |
|-----------|-----|------------|----------|
| `days` | `int` | `30` | Kaç günlük veri |

**Çıktı:** `List[SnapshotResponse]` - Tarih sıralı snapshot listesi

---

### 3.4 Analiz ve İstatistik

#### `POST /api/analyze`

**Amaç:** Seçili ürünler için AI analizi yapar.

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `product_ids` | `List[str]` | Ürün ID listesi |
| `question` | `str` | Opsiyonel soru |

**Çıktı:** `{"analysis": "AI tarafından üretilen analiz..."}}`

---

#### `GET /api/stats`

**Amaç:** Dashboard istatistiklerini döner.

**Çıktı:**
```json
{
    "total_products": 150,
    "total_snapshots": 450,
    "total_tasks": 25,
    "completed_tasks": 23,
    "total_sellers": 200,
    "total_reviews": 500
}
```

---

#### `GET /api/scraping/status`

**Amaç:** Proxy sağlayıcı durumlarını döner.

**Çıktı:**
```json
{
    "providers": [
        {"name": "scraperapi", "available": true},
        {"name": "brightdata", "available": true},
        {"name": "direct", "available": true}
    ],
    "current_provider": "scraperapi"
}
```

---

### 3.5 Background Task: `run_scraping_background(task_id)`

**Amaç:** Scraping işlemini arka planda çalıştırır.

**Akış:**
```
1. Task durumu: "running"
2. ScrapingService başlat
3. scrape_hepsiburada_search() çağır
4. Sponsorlu marka reklamlarını kaydet
5. Her ürün için:
   - Product varsa güncelle, yoksa oluştur
   - Günün snapshot'ı varsa güncelle, yoksa oluştur
   - Other sellers kaydet
   - Reviews kaydet (ilk kez)
6. Task durumu: "completed"
```

**Hata Durumunda:**
- Task durumu: "failed"
- error_message alanına hata yazılır

---

## 4. Veri Akış Diyagramı

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  Dashboard.tsx → POST /api/search { keyword: "oto şampuan" }    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      routes.py                                   │
│  create_search_task() → SearchTask(pending) → Background Task   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   scraping.py                                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ scrape_hepsiburada_search(keyword)                       │   │
│  │   ├── _get_product_urls_via_http_api(keyword)            │   │
│  │   │     └── _fetch_with_scraperapi_proxy(search_url)     │   │
│  │   │           └── _extract_product_urls_from_soup()      │   │
│  │   │           └── _extract_sponsored_brands_from_search()│   │
│  │   │                                                      │   │
│  │   └── For each URL:                                      │   │
│  │         └── scrape_product_detail_page(url)              │   │
│  │               ├── _scrape_product_via_http_api()         │   │
│  │               │     ├── _extract_utag_data()             │   │
│  │               │     ├── _extract_json_ld_data()          │   │
│  │               │     ├── _extract_html_data()             │   │
│  │               │     ├── _extract_other_sellers()         │   │
│  │               │     └── _extract_reviews()               │   │
│  │               │                                          │   │
│  │               └── [Fallback] _scrape_product_via_playwright()│
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   proxy_providers.py                             │
│                                                                  │
│  ProxyManager                                                    │
│    ├── ScraperAPIProvider (Primary)                             │
│    ├── BrightDataProvider (Fallback)                            │
│    └── DirectProvider (Last Resort)                             │
│                                                                  │
│  DebugLogger                                                     │
│    ├── log_request() → /tmp/scraping_debug/scraping.log        │
│    └── save_debug_html() → /tmp/scraping_debug/*.html           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL                                  │
│  ┌─────────────┐ ┌──────────────────┐ ┌───────────────────┐    │
│  │  Products   │ │ ProductSnapshots │ │ SponsoredBrandAds │    │
│  └─────────────┘ └──────────────────┘ └───────────────────┘    │
│  ┌─────────────┐ ┌──────────────────┐ ┌───────────────────┐    │
│  │ProductSellers│ │ ProductReviews  │ │   SearchTasks     │    │
│  └─────────────┘ └──────────────────┘ └───────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Önemli Sabitler

| Sabit | Değer | Açıklama |
|-------|-------|----------|
| `MAX_PRODUCTS_PER_SEARCH` | `8` | Arama başına maksimum ürün (maliyet kontrolü) |
| `MAX_RETRIES` | `2` | Maksimum yeniden deneme sayısı |
| `SCRAPERAPI_BASE_URL` | `http://api.scraperapi.com` | ScraperAPI HTTP endpoint |
| Proxy Port | `8001` | ScraperAPI proxy server portu |

---

## 6. Hata Yönetimi

| Durum | HTTP Kodu | Davranış |
|-------|-----------|----------|
| ScraperAPI render başarısız | 500 | Standart mode dene |
| ScraperAPI tamamen başarısız | - | Bright Data fallback |
| Playwright timeout | - | Devam et (product_data kısmi) |
| CAPTCHA/Robot detection | 403/429 | Debug HTML kaydet, fallback dene |
| Homepage redirect | - | Yeni session ile tekrar dene |

---

*Rapor Tarihi: 13 Aralık 2025*
