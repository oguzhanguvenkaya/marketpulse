# Faz 6: Temizlik ve Dokümantasyon — Netleştirilmiş Plan (2026-02-24, güncelleme: 2026-02-24)

## Context
Faz 6 planı kod bazında tekrar doğrulandı. Bu doküman artık "ne kaldı / ne tamamlandı / ne beklemede" ayrımını net gösterir.

## Özet Karar

| Track | Durum | Karar |
| --- | --- | --- |
| Track 1 (Backend Hygiene) | TAMAMLANDI | SKIP |
| Track 2 (Dependency & Security) | Ağ kısıtı + audit doğrulama eksik | BEKLEMEDE |
| Track 3 (Frontend Token Migration) | REGRESYON - Yeniden planlama gerekli | YENİDEN PLANLANACAK |

---

## 🛤️ TRACK 1: Backend Hygiene & Configuration
**Durum:** TAMAMLANDI
**Karar:** SKIP (yeni işlem yok)

### 1.1 Repo Temizliği
- `attached_assets/` ve `hepsiburada_active_products.json` `.gitignore` içinde.
- `git ls-files` çıktısı her iki hedef için `0`.
- Untrack işlemi geçmişte yapılmış: commit `d2d18d8`.

### 1.2 SCRAPPER -> SCRAPER_API_KEY Geçişi
- Fallback tuple hazır: `("SCRAPER_API_KEY", "SCRAPPER_API", "SCRAPPPER_API")`.
- Deprecation warning log'u mevcut.
- `transcript_service.py` artık `settings.SCRAPER_API_KEY` kullanıyor.

### 1.3 DEBUG_SAVE_HTML
- Varsayılan değer zaten `false`.

### 1.4 `.env.example`
- Dosya mevcut ve aktif kullanılan backend env değişkenleriyle uyumlu (commit `98aa497`).
- Otomasyon script'i bu aşamada zorunlu değil (tek geliştirici akışında over-engineering).

### 1.5 Dokümantasyon Temizliği
- `template_schema.md` ve `ui-ux-improvements-design.md` silindi (artık geçersiz).
- `SCRAPING_DEBUG_REPORT.md` arşivlendi: `docs/archive/` altına taşındı.

---

## 🛤️ TRACK 2: Dependency & Security Update
**Durum:** Kısmen uygulanmış, audit doğrulaması eksik  
**Karar:** BEKLEMEDE (internet erişimli ortamda finalize edilecek)

### 2.1 Mevcut Paket Durumu (runtime lock)
Aşağıdaki sürümler kurulu durumda:
- `react-router-dom@7.13.1`
- `react@19.2.4`
- `react-dom@19.2.4`
- `vite@7.3.1`
- `tailwindcss@4.2.1`
- `@tailwindcss/postcss@4.2.1`
- `plotly.js@3.4.0`
- `typescript-eslint@8.56.1`
- `eslint@9.39.3`

Not: `package.json` aralıkları (`^`) eski görünebilir; lock ve kurulu paketler daha güncel.

### 2.2 Güvenlik/Audit Durumu
- Lokal ortamda `npm audit` ağ kısıtı nedeniyle çalışmıyor (`ENOTFOUND registry.npmjs.org`).
- Bu nedenle "kaç high var ve tam kaynağı ne" çıktısı bu ortamda kesinlenemedi.

### 2.3 Track 2 Kapanış Koşulu
İnternet erişimli CI/dev ortamında:

```bash
cd frontend
npm audit
npm run build
```

- Audit raporu dosyalanacak.
- Kalan açıklar sadece dev-dependency ise risk notu ile kabul/erteleme kararı verilecek.

---

## 🛤️ TRACK 3: Frontend Token Migration
**Durum:** REGRESYON - Yeniden planlama gerekli
**Karar:** YENİDEN PLANLANACAK

### 3.0 Regresyon Notu (2026-02-24)

> **Ozet:** Token migration calismasi basarili bir sekilde ilerledi ancak sonraki accessibility commit'leri kazanimlari geri aldi.
>
> - 3 batch commit ile `dark:` sayisi **284 -> 87**'ye dusuruldu (commit'ler: `0a01fd8`, `8d12b76`, `62e2d7f`).
> - Ancak sonraki accessibility commit'leri (`444c181`, `422a6c5`) **195 yeni `dark:` class** ekledi.
> - Guncel `dark:` sayisi: **284** — baslangic degeriyle ayni.
> - Token migration calismasinin accessibility gereksinimleriyle uyumlu sekilde yeniden planlanmasi gerekiyor.

### 3.1 Guncel Metrikler (2026-02-24 guncelleme)
- `dark:` occurrence (TSX): **284** (baslangica geri dondu)
- Hardcoded hex: **~36 satir** (onceki 65 tahmini yanlisti)
- Bracket bazli hardcoded renk class satiri (`[...]`): **15**
- Semantic token'lar eklendi ve calisiyor (`index.css` `@theme` block)
- `index.css` icinde unique semantic color token (`--color-*`): **26** (light/dark eslenmis)

### 3.2 3 Batch Revize Uygulama

**Batch 1 (küçük etki):**
- Hedef: küçük dosyalarda kolay `dark:*` temizliği ve açık hardcoded class dönüşümü.
- Dosyalar: `ErrorBoundary`, `ConfirmDialog`, `ApiKeyModal`, `Skeleton`, `Layout`, `CategoryFilters`, `CategoryTree`, `DetailFetchPanel`, `ProductCards`, `ScraperPanel`, `MonitoredProductList`, `PriceMonitorFilters`, `SellerDetailPanel`, `Ads`.

**Batch 2 (orta etki):**
- Hedef: sayfa seviyesinde token standardizasyonu.
- Dosyalar: `CategoryExplorer`, `ProductDetail`, `SellerDetail`, `Sellers`, `Dashboard`, `Products`.

**Batch 3 (yüksek etki):**
- Hedef: en yoğun `dark:*` kullanan bileşenlerin satır-satır dönüşümü.
- Dosyalar: `UrlScraper`, `VideoTranscripts`, `ProductDetailModal`, `MarketplaceProductList`, `JsonEditor`.

### 3.3 Track 3 Kapanış Kriterleri

```bash
cd frontend
npx tsc --noEmit
npm run build
grep -roh 'dark:' src/ --include='*.tsx' | wc -l
grep -rn '#[0-9A-Fa-f]\{6\}' src/ --include='*.tsx'
```

Hedef (regresyon sonrasi revize):
- `dark:` sayisi `284` -> `<=50` (accessibility uyumlu sekilde)
- Hardcoded hex `~36` -> `<=10` (marka rengi/plotly ozel durumlari haric)
- Bracket hardcoded class satirlari `15` -> `<=5`
- Build ve type-check hatasiz
- **Onemli:** Accessibility commit'leriyle catisma olmayacak sekilde planlanmali

---

## Deployment Stratejisi
- Track 2 ve Track 3 ayrı PR/branch olarak yürütülecek.
- Track 1 için yeni PR açılmayacak (tamamlandı).
- Faz 6 kapanışı için final çıktılar:
  - Track 2 audit raporu
  - Track 3 migration diff + görsel doğrulama notları
