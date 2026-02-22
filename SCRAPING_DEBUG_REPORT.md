# Scraping Debug Report
**Date:** 2026-02-22
**Test Category:** Sıvı Cila (Hepsiburada)
**Test URL:** https://www.hepsiburada.com/sivi-cilalar-c-20035736
**Test Product:** https://www.hepsiburada.com/gyeon-q-m-wetcoat-nano-boya-koruma-ve-seramik-sprey-hizli-cila-1000-ml-su-itici-parlak-islak-cila-pm-HBC00007A82OF

---

## Tespit Edilen Sorunlar Ozeti

| # | Sorun | Etki | Kritiklik |
|---|-------|------|-----------|
| 1 | utagData JSON parse hatasi | brand, sku, barcode, seller_list, category_path hepsi bos | KRITIK |
| 2 | Kategori sayfasi fiyat parse hatasi | Bazi urunlerde absurt fiyatlar (151.126 TL) | KRITIK |
| 3 | Brand alani bos / 0 Brands gosterimi | Marka filtreleri ve istatistikler calismiyor | YUKSEK |
| 4 | Seller alanina marka adi yaziliyor | Satici filtreleri yanlis veri gosteriyor | ORTA |
| 5 | Detail fetch'te fiyat uzerine yazilmiyor | Yanlis kategori fiyatlari duzeltilmiyor | ORTA |

---

## BOLUM 1: KATEGORI SAYFASI KAZIMA (Category Page Scraping)

### 1.1 Scraping Sureci

Kategori sayfasi kazima `backend/app/services/category_scraper_service.py` dosyasinda gerceklestirilir.

**Adimlar:**
1. ScraperAPI ile kategori URL'si fetch edilir (or: `https://www.hepsiburada.com/sivi-cilalar-c-20035736`)
2. BeautifulSoup ile HTML parse edilir
3. Urun kartlari `<li class="productListContent...">` ile bulunur
4. Her karttaki bilgiler CSS class'larindan cikarilir

### 1.2 Urun Karti HTML Yapisi (Gercek Veri)

Hepsiburada'nin guncel urun karti yapisi:

```html
<li class="productListContent-...">
  <!-- Urun linki -->
  <a href="/meguiars-...-pm-HBC000XXXX" title="Meguiar's Ultimate Quik Wax...">
    
    <!-- Marka + Isim (H2 etiketi, H3 degil!) -->
    <h2>Meguiars Meguiar's Ultimate Quik Wax 473 ml...</h2>
    
    <!-- Gorsel -->
    <img src="https://productimages.hepsiburada.net/...">
    
    <!-- Fiyat Alani -->
    <div class="price-module_priceAreaRoot__MG440">
      
      <!-- Indirimli urunlerde: Orijinal fiyat + Indirim orani -->
      <div class="price-module_originalPriceArea__s-o4Z">
        <span class="price-module_originalPrice__43Wnd">1.325,17<!-- --> TL</span>
        <span class="price-module_discountRate__Uh-XD">%<!-- -->15</span>
      </div>
      
      <!-- Guncel satis fiyati -->
      <div class="price-module_finalPrice__LtjvY">
        1.126                                              <- TAM KISIM (dogrudan text node)
        <span class="price-module_finalPriceFraction__oALDy">
          ,39<!-- --> <!-- -->TL                            <- KURUS KISMI (child span)
        </span>
      </div>
      
    </div>
  </a>
</li>
```

### 1.3 FIYAT PARSE HATASI (KRITIK)

**Mevcut kod** (satir 384-396, `category_scraper_service.py`):
```python
price_text = price_area.get_text()  # -> "1.325,17TL%151.126,39TL"
price_candidates = re.findall(r'(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*TL', price_text)
```

**Sorun:** `get_text()` ile tum text aliniyor. Indirimli urunlerde CSS elementlerinin text'leri birlesince discount orani ile finalPrice birlesiyor.

**Nasil olusuyor (adim adim):**
1. `originalPrice` text: `"1.325,17 TL"`
2. `discountRate` text: `"%15"`
3. `finalPrice` text: `"1.126,39 TL"`
4. `get_text()` birlestirince: `"1.325,17TL%151.126,39TL"`
5. Regex ilk eslesme: `1.325,17` -> 1325.17 (dogru)
6. Ikinci eslesme: `151.126,39` (discount "%15" + finalPrice "1.126,39" birlesmis!)
7. `float('151126.39')` = 151126.39 <- YANLIS!
8. `max(parsed_prices)` = 151126.39 -> `original_price`'a yaziliyor

**Veritabaninda gorulen hatali fiyatlar:**

| Urun | DB'deki Fiyat (YANLIS) | Dogru Fiyat |
|------|------------------------|-------------|
| Meguiar's Ultimate Quik Wax | 151,126.39 TL | 1,126.39 TL |
| Trendwax T90 Tek Pasta | 101,124.10 TL | 1,124.10 TL |
| Gyeon Mohs Evo Light Box | 105,399.10 TL | 5,399.10 TL |
| Meguiar's Ultimate Polish | 151,616.14 TL | 1,616.14 TL |
| Meguiar's Ultimate Seramik | 152,417.53 TL | 2,417.53 TL |

**INDIRIMSIZ urunlerde sorun yok** cunku sadece `finalPrice` var, birlesme olmuyor.
**INDIRIMLI urunlerde sorun var** cunku `discountRate`'deki sayi finalPrice ile birlesiyor.

### 1.4 MARKA CIKARTMA

**Mevcut durum:**
- Kategori sayfasinda marka bilgisi `<h2>` etiketinden aliniyor
- `<h2>` etiketinde marka + urun adi birlikte yazili: `"Meguiars Meguiar's Ultimate Quik Wax..."`
- Mevcut kod `h2`'yi urun adi olarak kaydediyor, markayi ayristirmiyor
- `brand` alanina hicbir sey yazilmiyor

**Kategori sayfasi card'inda brand alani yok** - Hepsiburada ayri bir brand elementi sunmuyor.
Marka, urun adinin basinda yer aliyor (or: "Meguiars ...", "Trendwax ...", "Turtle Wax ...")

---

## BOLUM 2: URUN DETAY SAYFASI KAZIMA (Product Detail Scraping)

### 2.1 Scraping Sureci

Detay kazima `backend/app/api/category_explorer_routes.py` dosyasindaki `_fetch_single_detail_inner()` fonksiyonunda gerceklestirilir.

**Adimlar:**
1. DB'den urun URL'si alinir, session kapatilir
2. ScraperAPI ile urun detay sayfasi fetch edilir
3. 3 parse fonksiyonu calisir:
   - `_parse_utag_data(html)` -> JavaScript utagData objesi
   - `_parse_hb_specs(html)` -> Teknik ozellikler tablosu
   - `_parse_hb_description(html)` -> Urun aciklamasi
4. `url_scraper.parse_html(html, url)` -> JSON-LD, meta tag, genel HTML parsing (fallback)
5. Sonuclar DB'ye yazilir

### 2.2 utagData Raw Verisi (Gyeon WetCoat Urunu)

**Kaynak:** Hepsiburada urun sayfasinda `<script>` blogu icinde:
```javascript
utagData = { ... };
window.utagData = utagData;
```

**Tam raw utagData objesi:**
```json
{
  "canonical_url": "https://www.hepsiburada.com/gyeon-q-m-wetcoat-...-pm-HBC00007A82OF",
  "category_id_hierarchy": "60002705 > 2147483631 > 20035732 > 20035735 > 20035738",
  "category_name_hierarchy": "Yapi Market / Bahce / Oto > Oto Aksesuar > Arac Bakim Urunleri > Cila > Hizli Cila",
  "category_path": "/product/yapi-market-bahce-oto/oto-aksesuar/arac-bakim-urunleri/cila/hizli-cila/HBC00007A82OF",
  "is_canonical": "1",
  "listing_ids": ["35befa45-df8d-453b-aed0-4803bef33c12"],
  "merchant_ids": ["f2c7bb06-0bc8-463d-a3e7-e79030813ce7"],
  "merchant_names": ["TASDEMIR DETAY MARKET"],
  "new_site": "new",
  "order_currency": "TRY",
  "order_store": "TASDEMIR DETAY MARKET",
  "order_subtotal": ["1,349.00"],
  "page_domain": "www.hepsiburada.com",
  "page_language": "tr-TR",
  "page_name": "Product Detail",
  "page_site_name": "Hepsiburada",
  "page_site_region": "tr",
  "page_type": "pdp",
  "product_addInfo": [false],
  "product_barcode": "8683492661441",
  "product_barcodes": ["8683492661441"],
  "product_boosting_factors": [[]],
  "product_brand": "Gyeon",
  "product_brands": ["Gyeon"],
  "product_campaign_texts": [""],
  "product_categories": ["Yapi Market / Bahce / Oto", "Oto Aksesuar", "Arac Bakim Urunleri", "Cila", "Hizli Cila"],
  "product_category_ids": ["60002705", "2147483631", "20035732", "20035735", "20035738"],
  "product_ids": ["HBC00007A82OF"],
  "product_labels": [null],
  "product_name_array": "Gyeon Q2m WetCoat Nano Boya Koruma ve Seramik Sprey Hizli Cila - 1000 ml - Su Itici Parlak Islak Cila",
  "product_names": ["Gyeon Q2m WetCoat ... Cila"],
  "product_quantities": ["1"],
  "product_skus": ["HBCV00007A82OG"],
  "product_top_5": ["HBC00007A82OF"],
  "product_status": "InStock",
  "product_statuses": ["RemovedItem"],
  "review_count": "43",
  "review_rate": "4,8",
  "shipping_type": ["super-hizli"],
  "site_type": "desktop",
  "product_prices": ["1,349.00"],
  "product_unit_prices": ["1,349.00"],
  "page_deep_link": null,
  "index": "index",
  "follow": "follow"
}
```

### 2.3 utagData Alanlarinin Anlami

| Alan | Aciklama | Ornek Deger |
|------|----------|-------------|
| `product_brand` | **MARKA ADI** | `"Gyeon"` |
| `product_brands` | Marka listesi (array) | `["Gyeon"]` |
| `merchant_names` | **SATICI MAGAZA ADI** (marka DEGIL) | `["TASDEMIR DETAY MARKET"]` |
| `merchant_ids` | Satici UUID'leri | `["f2c7bb06-0bc8-..."]` |
| `order_store` | Aktif satici magaza adi | `"TASDEMIR DETAY MARKET"` |
| `product_skus` | SKU kodlari | `["HBCV00007A82OG"]` |
| `product_barcode` | Barkod (tek) | `"8683492661441"` |
| `product_barcodes` | Barkod listesi | `["8683492661441"]` |
| `product_prices` | Fiyat (Turkce format, virgullu) | `["1,349.00"]` |
| `review_rate` | Puan (Turkce format, virgullu) | `"4,8"` |
| `review_count` | Yorum sayisi | `"43"` |
| `category_name_hierarchy` | Kategori yolu | `"Yapi Market / Bahce / Oto > Oto Aksesuar > ..."` |
| `product_status` | Stok durumu | `"InStock"` |
| `shipping_type` | Kargo tipi | `["super-hizli"]` |

**ONEMLI FARK:**
- `product_brand` = **MARKA** (or: Gyeon, Meguiars, Turtle Wax)
- `merchant_names` = **SATICI** (or: TASDEMIR DETAY MARKET, Auto Detay Shop)
- Bunlar birbirinden tamamen farkli!

### 2.4 JSON-LD Verisi (Ayni Sayfa)

JSON-LD'de Product schema icinde:
```json
{
  "@type": "Product",
  "name": "Gyeon Q2m WetCoat ...",
  "brand": {
    "@type": "Brand",
    "name": "Gyeon"
  },
  "sku": "HBCV00007A82OG",
  "image": "https://productimages.hepsiburada.net/...",
  "offers": { ... }
}
```

### 2.5 UTAG PARSE HATASI (KRITIK SORUN #1)

**Mevcut regex** (`_parse_utag_data`):
```python
r'(?:const|var)\s+utagData\s*=\s*(\{.+?\});\s*\n'
```

**Gercek HTML'deki yapi:**
```javascript
utagData = {"canonical_url":"...", ...,"follow":"follow"}
            window.utagData = utagData;
            window.googletag = window.googletag || {cmd: []}
```

**Sorun - Regex yakalar AMA JSON parse basarisiz:**
- Regex `\{.+?\}` lazy match kullaniyor
- AMA `};\s*\n` ile kapanis ariyor ve birden fazla `}` satiri var
- Sonuc: regex yakalanan string `}` ile kapanmiyor, fazla text iceriyor
- `json.loads()` "Extra data" hatasi veriyor

**Test sonuclari:**
```
PRODUCTION REGEX MATCH: True (yakaliyor)
DIRECT JSON PARSE: FAILED - "Extra data: line 2 column 13 (char 1997)"

Hatanin oldugu yer:
..."index":"index","follow":"follow"}
            <<<HERE>>>window.utagData = utagData;
```

**Neden oluyor:**
Lazy `\{.+?\}` ilk `}` ile kapanmak yerine, regex'in `;\s*\n` requirement'i nedeniyle daha ileriye gidiyor.
Sonucta JSON objesinin sonundaki `}` + sonraki satirdaki text birlikte yakalaniyor.

**Dogru cozum - Balanced brace extraction:**
```python
start = html.find('utagData')
brace_start = html.find('{', start)
depth = 0
for i in range(brace_start, brace_start + 20000):
    if html[i] == '{': depth += 1
    elif html[i] == '}': depth -= 1
    if depth == 0:
        raw = html[brace_start:i+1]
        break
cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', raw)
data = json.loads(cleaned)
```

**Bu yontemle test:**
```
BALANCED PARSE: SUCCESS
product_brand: Gyeon
merchant_names: ['TASDEMIR DETAY MARKET']
product_prices: ['1,349.00']
product_skus: ['HBCV00007A82OG']
product_barcode: 8683492661441
review_rate: 4,8
review_count: 43
```

### 2.6 Parse Sonrasi Veri Esleme (Mevcut Kod vs Dogru Esleme)

**Mevcut kodda** (`_fetch_single_detail_inner`):

| Kaynak | Hedef Alan | Mevcut Davranis | Sorun |
|--------|-----------|-----------------|-------|
| `utag.product_brand` | `product.brand` | Dogru alan | Ama utag parse BASARISIZ oldugu icin bos |
| `utag.merchant_names[0]` | `product.seller_name` | Dogru alan | Parse basarisiz -> bos |
| *Fallback*: `parsed.seller_name` | `product.seller_name` | Bu aslinda HTML'den cikan "satici" | Bazen marka adi geliyor |
| `utag.product_prices` | `product.price` | Sadece mevcut fiyat bossa yaziliyor | Yanlis kategori fiyatini duzeltmiyor |

**utagData parse BASARILI oldugunda (duzeltme sonrasi beklenen):**

| Kaynak | Deger | Hedef |
|--------|-------|-------|
| `product_brand` | `"Gyeon"` | `product.brand` |
| `merchant_names` | `["TASDEMIR DETAY MARKET"]` | `product.seller_name` |
| `product_skus` | `["HBCV00007A82OG"]` | `product.sku` |
| `product_barcode` | `"8683492661441"` | `product.barcode` |
| `product_prices` | `["1,349.00"]` | `product.price` (her zaman guncelle) |
| `category_name_hierarchy` | `"Yapi Market > ... > Hizli Cila"` | `product.category_path` |
| `shipping_type` | `["super-hizli"]` | `product.shipping_type` |

---

## BOLUM 3: VERITABANI DURUMU (Mevcut Yanlis Veriler)

### 3.1 Brand Alani

```sql
SELECT DISTINCT brand FROM category_products 
WHERE brand IS NOT NULL AND brand != '';
-- SONUC: BOS (0 satir)
```

**47 urunun hicbirinde brand bilgisi yok** cunku utagData parse edilemedi.

### 3.2 Seller Alani

```sql
SELECT DISTINCT seller_name FROM category_products;
```
```
Alcon, Auto Glym, Autokit, Buzzard, Dyo, Fra-Ber, Gyeon, Gyeon Quartz,
Henkel, K2 PRO, Kunzel, Meguiars, Menzerna, Mirka, Newmix, Novaxir,
QWX Auto, Smx, Sonax, Stark Premium, Tonyin, Trendwax, Turtle Wax, Cbs
```

**Bunlar satici degil, MARKA isimleri!** Fallback HTML parsing'den marka adi `seller_name`'e yazilmis.
Gercek saticilar (TASDEMIR DETAY MARKET gibi) gelmemis cunku utag parse basarisiz.

### 3.3 Yanlis Fiyatlar

| ID | Urun | DB'deki (YANLIS) | Dogru (utag) |
|----|------|-------------------|--------------|
| 227 | Meguiar's Ultimate Quik Wax | 151,126.39 | 1,325.17 |
| 228 | Trendwax T90 Tek Pasta | 101,124.10 | 1,249.00 |
| 263 | Gyeon Mohs Evo Light Box | 105,399.10 | 5,999.00 |
| 264 | Meguiar's Ultimate Polish | 151,616.14 | 1,901.34 |
| 270 | Meguiar's Ultimate Seramik | 152,417.53 | 2,844.15 |

---

## BOLUM 4: DUZELTME PLANI

### Duzeltme 1: utagData Parse (KRITIK)
**Dosya:** `backend/app/api/category_explorer_routes.py` -> `_parse_utag_data()`

Balanced brace extraction yontemiyle degistirilecek:
1. `utagData = {` pattern'ini bul
2. `{` derinlik sayaci ile dogru kapanis `}` bul
3. Kontrol karakterlerini temizle
4. `json.loads()` uygula

### Duzeltme 2: Kategori Sayfasi Fiyat Parse (KRITIK)
**Dosya:** `backend/app/services/category_scraper_service.py`

`price_area.get_text()` yerine **finalPrice** elementini ayri parse et:
- `finalPrice` div'indeki dogrudan text node = tam kisim (or: "1.126")
- `finalPriceFraction` span'i = kurus kismi (or: ",39 TL")
- Birlestir: "1.126,39" -> `float('1126.39')`

### Duzeltme 3: Detail Fetch'te Fiyat Guncelleme
**Dosya:** `backend/app/api/category_explorer_routes.py` -> `_fetch_single_detail_inner()`

`if utag_price and not original_price:` -> `if utag_price:` (her zaman guncelle)

### Duzeltme 4: Brand Fallback (JSON-LD)
**Dosya:** `backend/app/api/category_explorer_routes.py`

utagData bos geldiginde JSON-LD'den `brand.name` cikar.

---

## BOLUM 5: RAW HTML ORNEKLERI

### 5.1 Kategori Sayfasi - Indirimli Urun Karti Fiyat HTML'i (Meguiar's)

```html
<div class="price-module_priceAreaRoot__MG440 price-module_isBasketCampaign__q1jch">
  <div class="price-module_priceLabel__GjxGJ" style="color:#009319">Sepete ozel</div>
  <div class="price-module_priceInfo__UTCQv">
    
    <!-- Orijinal fiyat + Indirim orani -->
    <div class="price-module_originalPriceArea__s-o4Z">
      <span class="price-module_originalPrice__43Wnd">1.325,17<!-- --> TL</span>
      <span class="price-module_discountRate__Uh-XD">%<!-- -->15</span>
    </div>
    
    <!-- Gercek satis fiyati -->
    <div class="price-module_finalPrice__LtjvY price-module_hasDiscount__...">
      1.126                                          <- DOGRUDAN TEXT NODE
      <span class="price-module_finalPriceFraction__oALDy">
        ,39<!-- --> <!-- -->TL                        <- KURUS + PARA BIRIMI
      </span>
    </div>
    
  </div>
</div>
```

### 5.2 Kategori Sayfasi - Indirimsiz Urun Karti Fiyat HTML'i (Alcon)

```html
<div class="price-module_priceAreaRoot__MG440">
  <div class="price-module_priceInfo__UTCQv">
    <div class="price-module_finalPrice__LtjvY" data-test-id="final-price-4">
      400                                            <- TAM FIYAT
      <span class="price-module_finalPriceFraction__oALDy">
        <!-- -->TL                                   <- KURUS YOK, SADECE TL
      </span>
    </div>
  </div>
</div>
```

### 5.3 Detay Sayfasi - utagData Script Blogu

```html
<script>
  utagData = {"canonical_url":"...", "product_brand":"Gyeon", "merchant_names":["TASDEMIR DETAY MARKET"], ...};
  window.utagData = utagData;
  window.googletag = window.googletag || {cmd: []}
</script>
```

**Not:** `utagData = { ... };` satir sonunda baska bir `window.utagData = utagData;` atamasi var.
Regex `.+?` lazy match ile `};` arayinca ilk `}` yerine ikinci satira kadar gidiyor.

---

## EK: Test Komutlari

### utagData Parse Test
```bash
cd backend && python3 -c "
import asyncio, re, json, sys
sys.path.insert(0, '.')
from app.services.url_scraper_service import UrlScraperService
scraper = UrlScraperService()

async def main():
    html = await scraper.fetch_url('URL_HERE')
    start = html.find('utagData')
    brace_start = html.find('{', start)
    depth = 0
    for i in range(brace_start, brace_start + 20000):
        if html[i] == '{': depth += 1
        elif html[i] == '}': depth -= 1
        if depth == 0:
            raw = html[brace_start:i+1]
            break
    cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', raw)
    data = json.loads(cleaned)
    print(json.dumps(data, indent=2, ensure_ascii=False))

asyncio.run(main())
"
```

### Veritabani Kontrol
```sql
-- Brand durumu
SELECT COUNT(*), COUNT(NULLIF(brand, '')) as with_brand FROM category_products;

-- Yanlis fiyatlar
SELECT id, name, price FROM category_products WHERE price > 10000;

-- Seller vs Brand karsilastirma
SELECT seller_name, brand, detail_data->>'brand' as utag_brand FROM category_products LIMIT 10;
```
