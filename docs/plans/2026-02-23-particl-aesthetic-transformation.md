# Particl Estetik Dönüşüm: Değerlendirme ve Uygulama Planı

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Kaynak:** `MarketPulse UI_UX Dönüşüm Raporu_ Particl Estetiği.md` (Manus AI, 23 Şubat 2026)

---

## 1. Raporun Değerlendirmesi

### Doğru Tespitler

| Tespit | Durum | Yorum |
|--------|-------|-------|
| Hardcoded hex değerler temizlenmeli | ✅ Kesinlikle doğru | 682 adet hardcoded renk değeri, 27 dosyada. Bu, herhangi bir tema değişikliğinin önündeki en büyük engel. |
| Renk paleti `@theme` üzerinden yönetilmeli | ✅ Zaten yapıldı | `@theme` bloğunu biz ekledik, Tailwind v4 utility sınıfları artık çalışıyor. |
| Dark mode `.dark` class override ile çalışmalı | ✅ Zaten çalışıyor | Mevcut yapı doğru, `.dark` override'ları aktif. |
| Boşluk (whitespace) artırılmalı | ✅ Geçerli öneri | Mevcut bileşenler sıkışık hissediyor. |

### Sorunlu/Eksik Noktalar

| Sorun | Detay |
|-------|-------|
| **Zaman tahmini gerçekçi değil** | Rapor "Faz 1: 1-2 gün" diyor. 682 hardcoded değeri temizlemek, her birini doğru semantic token'a eşlemek, light ve dark modda test etmek **minimum 3-5 gün**. |
| **Tailwind v4 farkı anlaşılmamış** | Rapor `@theme` bloğunu öneriyor ama Tailwind v4'ün `@theme` vs `:root` farkını açıklamıyor. (Biz bunu zaten çözdük.) |
| **`tailwind.config.js` duplicate sorunu yok sayılmış** | Hem `@theme` hem `tailwind.config.js`'de aynı renkler tanımlı. Bu potansiyel çakışma kaynaği. |
| **Light mode paleti radikal değişiklik** | Raporun önerdiği "saf beyaz + gri + yeşil aksan" paleti, mevcut "sıcak bal/krem" karakterinden **tamamen** farklı. Bu bir "iyileştirme" değil, "kimlik değişikliği". |
| **Bileşen düzeyinde detay eksik** | Rapor "kartları ve boş durumları yeniden tasarlayın" diyor ama 35 TSX dosyasının hangisinde ne yapılacağı belirsiz. |

### Stratejik Öneri

Raporun en değerli kısmı **Adım 2: Hardcoded Temizliği**. Bu adım palet-bağımsızdır ve mevcut "honey" temasında bile yapılmalı. Hardcoded değerler temizlendikten sonra, herhangi bir paleta geçiş (Particl dahil) **sadece `@theme` + `.dark` bloğunu değiştirmekle** mümkün olur.

**Önerilen Strateji:**
1. Önce tüm hardcoded değerleri semantic token'lara dönüştür (palet-bağımsız)
2. Sonra palet değişikliğini düşün (Particl veya başka)

---

## 2. Hardcoded Renk Envanteri ve Token Eşleştirmesi

### 2.1 Mevcut `@theme` Token'ları

```
--color-dark-900    Light: #fffbef   Dark: #0F1A17   → Ana arkaplan
--color-dark-800    Light: #f7eede   Dark: #162420   → Surface 1 / kart bg
--color-dark-700    Light: #fefbf0   Dark: #1C2E28   → Surface 2
--color-dark-600    Light: #e5e0d2   Dark: #243832   → Border
--color-dark-500    Light: #d4cfc1   Dark: #2A4039   → Border medium
--color-dark-400    Light: #9e9585   Dark: #6B8F80   → Muted text
--color-dark-300    Light: #7a7060   Dark: #A7C4B8   → Secondary text
--color-accent-primary    Light: #5b4824   Dark: #4ADE80
--color-accent-secondary  Light: #f7ce86   Dark: #22C55E
--color-accent-tertiary   Light: #e6ecd3   Dark: #86EFAC
--color-danger      Light: #cb5150   Dark: #ef7170
--color-warning     Light: #d97706   Dark: #fbbf24
--color-success     Light: #16a34a   Dark: #4ade80
```

### 2.2 Eksik Token'lar (Eklenmesi Gerekenler)

Hardcoded değerlerin analizi, mevcut token'ların bazı renk ihtiyaçlarını karşılamadığını gösteriyor:

| Yeni Token | Light Mode Değer | Dark Mode Değer | Kullanım | Mevcut Hardcoded |
|------------|------------------|-----------------|----------|------------------|
| `--color-text-primary` | `#0f1419` | `#F0FDF4` | Başlıklar, güçlü metin | `text-[#0f1419]` / `dark:text-[#F0FDF4]` |
| `--color-text-secondary` | `#3d3427` | `#A7C4B8` | Normal gövde metni | `text-[#3d3427]` / `dark:text-[#A7C4B8]` |
| `--color-text-muted` | `#9e8b66` | `#6B8F80` | Label, placeholder, ipucu | `text-[#9e8b66]` / `dark:text-[#6B8F80]` |
| `--color-text-body` | `#5f471d` | `#A7C4B8` | Genel gövde metni | `text-[#5f471d]` / `dark:text-[#A7C4B8]` |
| `--color-surface-input` | `#fffbef` | `#0F1A17` | Input arkaplanı | `bg-[#fffbef]` / `dark:bg-[#0F1A17]` |
| `--color-surface-card` | `#fefbf0` | `#162420` | Kart arkaplanı | `bg-[#fefbf0]` / `dark:bg-[#162420]` |
| `--color-surface-subtle` | `#f7eede` | `#162420` | Hafif arkaplan, resim bg | `bg-[#f7eede]` / `dark:bg-[#162420]` |
| `--color-border-default` | `#e5e0d2` | `#2A4039` | Standart border | `border-[#e5e0d2]` / `dark:border-[#2A4039]` |
| `--color-border-input` | `#e8dfcf` | `#2A4039` | Input border | `border-[#e8dfcf]` / `dark:border-[#2A4039]` |

### 2.3 Hardcoded → Semantic Token Eşleştirme Tablosu

Bu tablo, replace_all işlemlerinde kullanılacak eşleştirmeyi gösterir:

**Text renkleri:**

| Hardcoded Pattern | Semantic Replacement | Adet (tahmini) |
|-------------------|---------------------|----------------|
| `text-[#0f1419] dark:text-[#F0FDF4]` | `text-text-primary` | ~60 |
| `text-[#3d3427] dark:text-[#A7C4B8]` | `text-text-secondary` | ~25 |
| `text-[#9e8b66] dark:text-[#6B8F80]` | `text-text-muted` | ~80 |
| `text-[#5f471d] dark:text-[#A7C4B8]` | `text-text-body` | ~30 |
| `text-[#5b4824] dark:text-[#4ADE80]` | `text-accent-primary` | ~15 |
| `text-[#7a6b4e] dark:text-[#A7C4B8]` | `text-dark-300` | ~10 |

**Background renkleri:**

| Hardcoded Pattern | Semantic Replacement | Adet (tahmini) |
|-------------------|---------------------|----------------|
| `bg-[#f7eede] dark:bg-[#162420]` | `bg-surface-subtle` | ~30 |
| `bg-[#fefbf0] dark:bg-[#162420]` | `bg-surface-card` | ~15 |
| `bg-[#fffbef] dark:bg-[#0F1A17]` | `bg-surface-input` | ~10 |
| `bg-[#162420]` (dark only) | `dark:bg-dark-800` | ~20 |
| `bg-[#5b4824]/5 dark:bg-[#4ADE80]/5` | `bg-accent-primary/5` | ~40 |
| `bg-[#5f471d] dark:bg-[#4ADE80]` | `bg-accent-primary` | ~5 |

**Border renkleri:**

| Hardcoded Pattern | Semantic Replacement | Adet (tahmini) |
|-------------------|---------------------|----------------|
| `border-[#e5e0d2] dark:border-[#2A4039]` | `border-border-default` | ~60 |
| `border-[#e8dfcf] dark:border-[#2A4039]` | `border-border-input` | ~10 |
| `border-[#2A4039]` (dark only) | `dark:border-dark-500` | ~5 |

**Dikkat: Opacity pattern'ler**

`bg-[#5b4824]/5` gibi opacity pattern'ler doğrudan token'a çevrilemez. Bunlar için:
- `bg-accent-primary/5` → Tailwind v4'de `bg-accent-primary/5` çalışır (opacity modifier)
- Veya CSS class: `.bg-accent-subtle { background: color-mix(in srgb, var(--color-accent-primary) 5%, transparent); }`

---

## 3. Uygulama Planı

### Faz 0: Altyapı Hazırlığı (Önkoşul)

#### Task 0.1 — `@theme`'e yeni token'ları ekle

**Dosyalar:**
- Modify: `frontend/src/index.css` (satır 5-21 arası @theme bloğu)

**Adım 1:** `@theme` bloğuna yeni token'ları ekle:

```css
@theme {
  /* Mevcut token'lar aynı kalır */
  --color-dark-900: #fffbef;
  --color-dark-800: #f7eede;
  --color-dark-700: #fefbf0;
  --color-dark-600: #e5e0d2;
  --color-dark-500: #d4cfc1;
  --color-dark-400: #9e9585;
  --color-dark-300: #7a7060;

  --color-accent-primary: #5b4824;
  --color-accent-secondary: #f7ce86;
  --color-accent-tertiary: #e6ecd3;

  --color-danger: #cb5150;
  --color-warning: #d97706;
  --color-success: #16a34a;

  /* YENİ: Semantic text token'ları */
  --color-text-primary: #0f1419;
  --color-text-secondary: #3d3427;
  --color-text-muted: #9e8b66;
  --color-text-body: #5f471d;

  /* YENİ: Semantic surface token'ları */
  --color-surface-input: #fffbef;
  --color-surface-card: #fefbf0;
  --color-surface-subtle: #f7eede;

  /* YENİ: Semantic border token'ları */
  --color-border-default: #e5e0d2;
  --color-border-input: #e8dfcf;
}
```

**Adım 2:** `.dark` bloğuna karşılık gelen override'ları ekle:

```css
.dark {
  /* Mevcut override'lar aynı kalır */

  /* YENİ: Semantic text overrides */
  --color-text-primary: #F0FDF4;
  --color-text-secondary: #A7C4B8;
  --color-text-muted: #6B8F80;
  --color-text-body: #A7C4B8;

  /* YENİ: Semantic surface overrides */
  --color-surface-input: #0F1A17;
  --color-surface-card: #162420;
  --color-surface-subtle: #162420;

  /* YENİ: Semantic border overrides */
  --color-border-default: #2A4039;
  --color-border-input: #2A4039;
}
```

**Adım 3:** `npm run build` — başarılı olmalı.

**Adım 4:** Commit: `feat(theme): add semantic text/surface/border tokens to @theme`

---

#### Task 0.2 — `tailwind.config.js` ile `@theme` çakışmasını çöz

**Dosyalar:**
- Modify: `frontend/tailwind.config.js`

**Sorun:** Hem `tailwind.config.js` hem `@theme` aynı renkleri tanımlıyor. Tailwind v4'de `@theme` ana kaynaktır.

**Adım 1:** `tailwind.config.js`'den `colors` objesindeki `dark`, `accent` anahtarlarını kaldır (bunlar `@theme`'de zaten var).

**Adım 2:** `success`, `warning`, `danger` renklerini de kaldır (bunlar da `@theme`'de var).

**Adım 3:** Sadece `@theme`'de olmayan değerleri bırak:
- `neutral` renkleri → bu da `@theme`'e taşınabilir veya kaldırılabilir (kullanılıp kullanılmadığı kontrol edilmeli)
- `boxShadow`, `backgroundImage`, `animation`, `keyframes`, `borderRadius`, `fontFamily` → bunlar kalabilir

**Adım 4:** `npm run build` — başarılı olmalı.

**Adım 5:** Commit: `refactor(theme): remove duplicate color definitions from tailwind.config.js`

---

### Faz 1: Hardcoded Değer Temizliği (Büyük Dosyalar Önce)

Her dosya için strateji: `replace_all` ile en yaygın pattern'leri değiştir, sonra kalan hardcoded'ları tek tek incele.

#### Dosya Büyüklüğüne Göre Öncelik Sıralaması

| Sıra | Dosya | Tahmini Hardcoded Sayısı |
|------|-------|--------------------------|
| 1 | `components/MarketplaceProductList.tsx` | ~140 |
| 2 | `pages/Dashboard.tsx` | ~70 |
| 3 | `pages/SellerDetail.tsx` | ~50 |
| 4 | `pages/Sellers.tsx` | ~45 |
| 5 | `pages/ProductDetail.tsx` | ~45 |
| 6 | `pages/Ads.tsx` | ~40 |
| 7 | `pages/CategoryExplorer.tsx` | ~30 |
| 8 | `pages/UrlScraper.tsx` | ~30 |
| 9 | `pages/JsonEditor.tsx` | ~30 |
| 10 | `pages/VideoTranscripts.tsx` | ~25 |
| 11 | `components/Layout.tsx` | ~25 |
| 12 | `pages/Products.tsx` | ~20 |
| 13 | `components/category-explorer/ProductDetailModal.tsx` | ~20 |
| 14 | `components/category-explorer/ProductCards.tsx` | ~15 |
| 15 | `components/category-explorer/ScraperPanel.tsx` | ~15 |
| 16 | `components/category-explorer/DetailFetchPanel.tsx` | ~12 |
| 17 | `components/category-explorer/CategoryFilters.tsx` | ~10 |
| 18 | `components/category-explorer/CategoryTree.tsx` | ~10 |
| 19 | `components/price-monitor/MonitoredProductList.tsx` | ~15 |
| 20 | `components/price-monitor/PriceMonitorFilters.tsx` | ~10 |
| 21 | `components/price-monitor/SellerDetailPanel.tsx` | ~10 |
| 22 | `components/price-monitor/DeleteModal.tsx` | ~8 |
| 23 | `components/price-monitor/ImportModal.tsx` | ~8 |
| 24 | `components/ApiKeyModal.tsx` | ~15 |
| 25 | `components/Sparkline.tsx` | ~3 |
| 26 | `components/ErrorBoundary.tsx` | ~3 |
| 27 | `components/ConfirmDialog.tsx` | ~3 |

#### Task 1.x — Her dosya için aynı prosedür

Her dosya için:

**Adım 1:** Dosyayı oku, tüm `[#...]` pattern'lerini tespit et.

**Adım 2:** Aşağıdaki standart replace_all'ları uygula (sırayla):

```
# Text replace'leri (light+dark pair olarak)
text-[#0f1419] dark:text-[#F0FDF4]  →  text-text-primary
text-[#3d3427] dark:text-[#A7C4B8]  →  text-text-secondary
text-[#9e8b66] dark:text-[#6B8F80]  →  text-text-muted
text-[#5f471d] dark:text-[#A7C4B8]  →  text-text-body
text-[#5b4824] dark:text-[#4ADE80]  →  text-accent-primary
text-[#7a6b4e] dark:text-[#A7C4B8]  →  text-dark-300

# Background replace'leri (light+dark pair olarak)
bg-[#f7eede] dark:bg-[#162420]    →  bg-surface-subtle
bg-[#fefbf0] dark:bg-[#162420]    →  bg-surface-card
bg-[#fffbef] dark:bg-[#0F1A17]    →  bg-surface-input

# Opacity pattern replace'leri
bg-[#5b4824]/5 dark:bg-[#4ADE80]/5    →  bg-accent-primary/5
bg-[#5b4824]/8 dark:bg-[#4ADE80]/8    →  bg-accent-primary/[0.08]
hover:bg-[#5b4824]/5 dark:hover:bg-[#4ADE80]/5    →  hover:bg-accent-primary/5
hover:bg-[#5b4824]/8 dark:hover:bg-[#4ADE80]/8    →  hover:bg-accent-primary/[0.08]

# Border replace'leri (light+dark pair olarak)
border-[#e5e0d2] dark:border-[#2A4039]  →  border-border-default
border-[#e8dfcf] dark:border-[#2A4039]  →  border-border-input

# Gradient/karmaşık pattern'ler → dosya bazında manuel inceleme
```

**Adım 3:** Kalan hardcoded değerleri tek tek incele (gradient, from/to, placeholder, focus ring gibi özel durumlar).

**Adım 4:** `npm run build` — hatasız olmalı.

**Adım 5:** Commit: `refactor(theme): replace hardcoded colors in <DosyaAdı>`

---

### Faz 1 Batch'leri

**Batch 1 (En büyük dosyalar):**
- Task 1.1: `MarketplaceProductList.tsx` (~140 değer)
- Task 1.2: `Dashboard.tsx` (~70 değer)
- Task 1.3: `SellerDetail.tsx` (~50 değer)

**Batch 2 (Büyük sayfalar):**
- Task 1.4: `Sellers.tsx` (~45 değer)
- Task 1.5: `ProductDetail.tsx` (~45 değer)
- Task 1.6: `Ads.tsx` (~40 değer)

**Batch 3 (Orta sayfalar):**
- Task 1.7: `CategoryExplorer.tsx` (~30 değer)
- Task 1.8: `UrlScraper.tsx` (~30 değer)
- Task 1.9: `JsonEditor.tsx` (~30 değer)
- Task 1.10: `VideoTranscripts.tsx` (~25 değer)

**Batch 4 (Layout + Products):**
- Task 1.11: `Layout.tsx` (~25 değer)
- Task 1.12: `Products.tsx` (~20 değer)

**Batch 5 (category-explorer bileşenleri):**
- Task 1.13: `ProductDetailModal.tsx` (~20 değer)
- Task 1.14: `ProductCards.tsx` (~15 değer)
- Task 1.15: `ScraperPanel.tsx` (~15 değer)
- Task 1.16: `DetailFetchPanel.tsx` (~12 değer)
- Task 1.17: `CategoryFilters.tsx` (~10 değer)
- Task 1.18: `CategoryTree.tsx` (~10 değer)

**Batch 6 (price-monitor bileşenleri):**
- Task 1.19: `MonitoredProductList.tsx` (~15 değer)
- Task 1.20: `PriceMonitorFilters.tsx` (~10 değer)
- Task 1.21: `SellerDetailPanel.tsx` (~10 değer)
- Task 1.22: `DeleteModal.tsx` (~8 değer)
- Task 1.23: `ImportModal.tsx` (~8 değer)

**Batch 7 (Küçük bileşenler):**
- Task 1.24: `ApiKeyModal.tsx` (~15 değer)
- Task 1.25: `Sparkline.tsx` (~3 değer)
- Task 1.26: `ErrorBoundary.tsx` (~3 değer)
- Task 1.27: `ConfirmDialog.tsx` (~3 değer)

---

### Faz 1 Tamamlama

**Task 1.28 — Final doğrulama:**

**Adım 1:** `grep -r "text-\[#\|bg-\[#\|border-\[#" frontend/src/ --include="*.tsx" | wc -l` → 0 olmalı (veya bilerek bırakılanlar kayıt altında olmalı).

**Adım 2:** `npm run build` — hatasız.

**Adım 3:** Tarayıcıda hem light hem dark mode'u elle kontrol et (özellikle Dashboard, Products, UrlScraper sayfaları).

**Adım 4:** Commit: `refactor(theme): complete hardcoded color cleanup — all values now use semantic tokens`

---

### Faz 2: CSS Bileşen Sınıflarını Temizle (Opsiyonel)

`index.css`'deki `.card-dark`, `.input-dark`, `.btn-primary`, `.table-dark` gibi sınıflarda da hardcoded renkler var. Bunları da semantic token'lara bağlamak tutarlılık sağlar.

**Task 2.1:** `index.css`'deki tüm bileşen sınıflarında hardcoded hex → `var(--color-*)` dönüşümü.

---

### Faz 3: Particl Palet Değişikliği (Opsiyonel / Kullanıcı Kararı)

> ⚠️ Bu faz, Faz 1 tamamlandıktan sonra yalnızca `@theme` + `.dark` bloğundaki ~25 satırı değiştirerek uygulanabilir.

Raporun önerdiği Particl paleti:

```css
@theme {
  --color-dark-900: #ffffff;      /* Saf Beyaz */
  --color-dark-800: #f8f9fa;      /* Çok Açık Gri */
  --color-dark-700: #f1f3f5;      /* Açık Gri */
  --color-dark-600: #dee2e6;      /* Border */
  --color-dark-500: #adb5bd;      /* Border Medium */
  --color-dark-400: #868e96;      /* Muted Text */
  --color-dark-300: #495057;      /* Secondary Text */

  --color-accent-primary: #4ADE80;  /* Parlak Yeşil */
  --color-accent-secondary: #22C55E;
  --color-accent-tertiary: #86EFAC;

  --color-text-primary: #212529;
  --color-text-secondary: #495057;
  --color-text-muted: #868e96;
  --color-text-body: #343a40;

  --color-surface-input: #ffffff;
  --color-surface-card: #ffffff;
  --color-surface-subtle: #f8f9fa;

  --color-border-default: #e9ecef;
  --color-border-input: #ced4da;
}
```

Bu değişiklik, mevcut "sıcak bal/krem" kimliğini "soğuk gri/beyaz" ile değiştirir. **Kullanıcı bu tercihi yapmalıdır.**

---

## 4. Doğrulama Kontrol Listesi

Her batch sonrasında:
- [ ] `npm run build` hatasız
- [ ] `grep` ile kalan hardcoded sayısı azalıyor
- [ ] Light mode: metin okunabilir, arka planlar doğru, border'lar görünür
- [ ] Dark mode: aynı kontroller
- [ ] Butonlar tıklanabilir görünüyor, disabled state çalışıyor
- [ ] Gradient'ler ve opacity pattern'ler kırılmamış

---

## 5. Risk ve Dikkat Noktaları

1. **Pair replace kritik:** `text-[#0f1419] dark:text-[#F0FDF4]` → `text-text-primary` yapılırken, light ve dark değerler **birlikte** replace edilmeli. Sadece birini değiştirmek, diğer mod'u kırar.

2. **Bazı değerler eşleşmeyebilir:** Örneğin `text-[#0f1419]` dark olmadan tek kullanılmış olabilir. Bu durumda sadece `text-text-primary` yeterli (dark mode override otomatik).

3. **Gradient ve `from-/to-` pattern'ler:** `from-[#fefbf0] to-[#fffbef] dark:from-[#162420] dark:to-[#0F1A17]` gibi pattern'ler için yeni gradient token'ları gerekebilir veya `from-surface-card to-surface-input dark:from-dark-800 dark:to-dark-900` kullanılabilir.

4. **Focus ring renkleri:** `focus:ring-[#5f471d]/30 dark:focus:ring-[#4ADE80]/30` → `focus:ring-accent-primary/30` olabilir.

5. **Placeholder renkleri:** `placeholder:text-[#9e8b66] dark:placeholder:text-[#6B8F80]` → `placeholder:text-text-muted`
