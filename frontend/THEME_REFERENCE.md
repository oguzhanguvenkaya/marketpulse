# MarketPulse Theme Reference

> Bu dosya uygulamanin tum tema bilgilerini icerir. Son guncelleme: 2026-02-23

---

## 1. Tema Mimarisi

| Katman | Dosya | Aciklama |
|--------|-------|----------|
| Tailwind v4 Theme | `src/index.css` `@theme` blogu | Utility class uretimi (`bg-accent-primary`, `text-danger` vb.) |
| CSS Variables | `src/index.css` `:root` / `.dark` | Runtime degisen surface/shadow degiskenleri |
| Tailwind Config | `tailwind.config.js` | Eski config (v3 uyumlu), bazi ek tokenlar |
| PostCSS | `postcss.config.js` | `@tailwindcss/postcss` plugin |
| Dark Mode | `Layout.tsx` | `class` tabanlı, localStorage: `mp_theme` |

**Dark mode toggle:** `document.documentElement.classList.toggle('dark', theme === 'dark')`

---

## 2. Renk Paleti

### 2.1 Tema Renkleri (`@theme` blogu — Tailwind v4 utility uretir)

| Token | Light Mode | Dark Mode | Kullanim |
|-------|-----------|-----------|----------|
| `--color-dark-900` | `#fffbef` | `#0F1A17` | En dis arka plan / en acik beyaz |
| `--color-dark-800` | `#f7eede` | `#162420` | Surface 1 |
| `--color-dark-700` | `#fefbf0` | `#1C2E28` | Surface 2 / kart ici |
| `--color-dark-600` | `#e5e0d2` | `#243832` | Border light |
| `--color-dark-500` | `#d4cfc1` | `#2A4039` | Border medium |
| `--color-dark-400` | `#9e9585` | `#6B8F80` | Muted text |
| `--color-dark-300` | `#7a7060` | `#A7C4B8` | Secondary text |
| `--color-accent-primary` | `#5b4824` | `#4ADE80` | Ana vurgu — butonlar, linkler |
| `--color-accent-secondary` | `#f7ce86` | `#22C55E` | Ikincil vurgu |
| `--color-accent-tertiary` | `#e6ecd3` | `#86EFAC` | Ucuncu vurgu |
| `--color-danger` | `#cb5150` | `#ef7170` | Hata / price alert |
| `--color-warning` | `#d97706` | `#fbbf24` | Uyari / campaign alert |
| `--color-success` | `#16a34a` | `#4ade80` | Basari |

### 2.2 Surface / Shadow Degiskenleri (`:root` / `.dark` — utility uretmez)

| Token | Light Mode | Dark Mode |
|-------|-----------|-----------|
| `--surface-base` | `rgba(255,251,239, 0.96)` | `rgba(15,26,23, 0.96)` |
| `--surface-raised` | `rgba(254,251,240, 0.98)` | `rgba(28,46,40, 0.98)` |
| `--surface-border` | `rgba(91,72,36, 0.15)` | `rgba(74,222,128, 0.12)` |
| `--surface-border-strong` | `rgba(91,72,36, 0.3)` | `rgba(74,222,128, 0.25)` |
| `--shadow-strong` | `0 20px 60px rgba(91,72,36, 0.1)` | `0 20px 60px rgba(0,0,0, 0.3)` |

### 2.3 Hardcoded Hex Renkleri (TSX dosyalarindaki arbitrary values)

#### Light Mode Paleti
| Hex | Kullanim |
|-----|----------|
| `#0f1419` | Ana koyu metin |
| `#3a2d14` | Baslik / aktif metin |
| `#3d3427` | Menu itemlari |
| `#5b4824` | Accent primary (kahve) |
| `#5f471d` | Sekonder metin |
| `#7a6b4e` | Tersiyer metin |
| `#9e8b66` | Muted metin (label) |
| `#b5a382` | Cok soluk metin |
| `#e5e0d2` | Border light |
| `#e8dfcf` | Hover state |
| `#f0e8d8` | Arka plan varyanti |
| `#f7ce86` | Altin / accent secondary |
| `#f7eede` | Surface |
| `#fefbf0` | Surface varyanti |
| `#fffbef` | Beyaz / krem |
| `#ff6000` | Turuncu ozel vurgu |

#### Dark Mode Paleti
| Hex | Kullanim |
|-----|----------|
| `#0F1A17` | Ana arka plan |
| `#162420` | Surface 1 |
| `#1C2E28` | Surface 2 |
| `#2A4039` | Surface 3 / border |
| `#022c22` | Buton metni (accent bg uzerinde) |
| `#4ADE80` | Accent primary (parlak yesil) |
| `#6B8F80` | Muted metin |
| `#A7C4B8` | Sekonder metin |
| `#F0FDF4` | Ana acik metin |

---

## 3. Tipografi

### Font Ailesi
| Aile | Font | Agirliklar | Kullanim |
|------|------|-----------|----------|
| Sans | Inter | 400, 500, 600, 700, 800 | Genel metin, butonlar |
| Serif | Lora | 400, 500, 600, 700 | Basliklar (h1-h6) |
| Mono | Space Grotesk | 400, 500, 600, 700 | Kod, JSON editor |

### CSS Tanimlar
```css
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
h1-h6 { font-family: 'Lora', 'Inter', serif; letter-spacing: -0.02em; }
```

---

## 4. Komponent Stilleri

### 4.1 Butonlar

#### `.btn-primary`
| Ozellik | Light | Dark |
|---------|-------|------|
| Background | `var(--color-accent-primary)` (#5b4824) | `#4ADE80` |
| Color | `#ffffff` | `#022c22` |
| Padding | `0.66rem 1.28rem` | ayni |
| Border Radius | `0.875rem` | ayni |
| Hover | `translateY(-1px)`, shadow | shadow `rgba(74,222,128, 0.25)` |
| Disabled | `opacity: 0.55` | ayni |

#### `.btn-secondary`
| Ozellik | Light | Dark |
|---------|-------|------|
| Background | `rgba(91,72,36, 0.08)` | `rgba(74,222,128, 0.1)` |
| Color | `#5b4824` | `#4ADE80` |
| Border | `1px solid rgba(91,72,36, 0.2)` | `rgba(74,222,128, 0.2)` |

#### `.btn-danger`
| Ozellik | Light | Dark |
|---------|-------|------|
| Background | `rgba(203,81,80, 0.1)` | `rgba(203,81,80, 0.15)` |
| Color | `#cb5150` | `#ef7170` |
| Border | `1px solid rgba(203,81,80, 0.25)` | `rgba(203,81,80, 0.3)` |

### 4.2 Kartlar

#### `.card-dark`
| Ozellik | Light | Dark |
|---------|-------|------|
| Background | `#fefbf0` | `#1C2E28` |
| Border | `1px solid var(--surface-border)` | ayni (degisken degisir) |
| Border Radius | `14px` (mobile: `12px`) | ayni |
| Shadow | `0 4px 16px rgba(91,72,36, 0.06)` | `rgba(0,0,0, 0.2)` |
| Hover Shadow | `0 8px 28px rgba(91,72,36, 0.1)` | `rgba(0,0,0, 0.3)` |

#### `.stat-card`
| Ozellik | Light | Dark |
|---------|-------|------|
| Background | `#fefbf0` | `#1C2E28` |
| Top accent | gradient bar (`--stat-color`) | ayni |

### 4.3 Badge'ler

| Sinif | Light Color | Dark Color | Light BG | Dark BG |
|-------|------------|------------|----------|---------|
| `.badge-success` | `#16a34a` | `#4ade80` | `rgba(34,163,74, 0.1)` | `rgba(34,197,94, 0.15)` |
| `.badge-warning` | `#d97706` | `#fbbf24` | `rgba(245,158,11, 0.1)` | `rgba(245,158,11, 0.15)` |
| `.badge-danger` | `#cb5150` | `#ef7170` | `rgba(203,81,80, 0.1)` | `rgba(203,81,80, 0.15)` |
| `.badge-info` | `#5b4824` | `#4ADE80` | `rgba(91,72,36, 0.08)` | `rgba(74,222,128, 0.1)` |
| `.badge-neutral` | `#7a7060` | `#6B8F80` | `rgba(158,149,133, 0.1)` | `rgba(107,143,128, 0.15)` |

### 4.4 Input

#### `.input-dark`
| Ozellik | Light | Dark |
|---------|-------|------|
| Background | `#ffffff` | `#162420` |
| Border | `1px solid #e5e0d2` | `#243832` |
| Color | `#0f1419` | `#F0FDF4` |
| Focus Border | `#5b4824` | `#4ADE80` |
| Focus Shadow | `0 0 0 3px rgba(91,72,36, 0.12)` | `rgba(74,222,128, 0.15)` |
| Placeholder | `#9e9585` | `#6B8F80` |

### 4.5 Tablo

#### `.table-dark`
| Ozellik | Light | Dark |
|---------|-------|------|
| Header BG | `rgba(247,238,222, 0.6)` | `rgba(36,56,50, 0.6)` |
| Header Color | `#7a7060` | `#A7C4B8` |
| Cell Color | `#0f1419` | `#F0FDF4` |
| Row Hover | `rgba(247,206,134, 0.1)` | `rgba(74,222,128, 0.06)` |

### 4.6 Navigasyon

#### `.nav-item`
| Ozellik | Light Hover | Dark Hover |
|---------|------------|------------|
| Border | `rgba(91,72,36, 0.15)` | `rgba(74,222,128, 0.15)` |
| Background | `rgba(247,206,134, 0.12)` | `rgba(74,222,128, 0.08)` |

#### `.nav-item-active`
| Ozellik | Light | Dark |
|---------|-------|------|
| Border | `rgba(91,72,36, 0.25)` | `rgba(74,222,128, 0.25)` |
| Background | `linear-gradient(#f7ce86 20%, #e6ecd3 15%)` | `linear-gradient(#4ADE80 12%, #86EFAC 10%)` |
| Animasyon | `glowPulse 1.6s infinite alternate` | ayni |

### 4.7 Sidebar & Topbar

| Sinif | Light | Dark |
|-------|-------|------|
| `.sidebar-surface` BG | `#fefbf0` | `#162420` |
| `.sidebar-surface` Border | `rgba(91,72,36, 0.12)` | `rgba(74,222,128, 0.08)` |
| `.topbar-surface` BG | `rgba(255,251,239, 0.88)` + `blur(14px)` | `rgba(15,26,23, 0.88)` |
| `.brand-mark` | `gradient(#f7ce86, #5b4824)` | `gradient(#4ADE80, #22C55E)` |

---

## 5. Animasyonlar

### CSS Keyframes (`index.css`)

| Animasyon | Adi | Sure | Davranis |
|-----------|-----|------|----------|
| `fadeIn` | `.animate-fade-in` | 0.34s ease-out | opacity 0→1, translateY 10px→0 |
| `slideIn` | `.animate-slide-in` | 0.32s ease-out | opacity 0→1, translateX -16px→0 |
| `glowPulse` | (nav-item-active) | 1.6s infinite alternate | box-shadow pulse |

### Tailwind Keyframes (`tailwind.config.js`)

| Animasyon | Adi | Sure | Davranis |
|-----------|-----|------|----------|
| `glow` | `animate-glow` | 2.2s infinite alternate | box-shadow 4px→16px |
| `shimmer` | `animate-shimmer` | 1.5s infinite | translateX 0→100% |
| `pulse` | `animate-pulse-slow` | 3s infinite | Standart pulse |

---

## 6. Scrollbar Stilleri

### Genel Scrollbar (`::-webkit-scrollbar`)

| Ozellik | Light | Dark |
|---------|-------|------|
| Width/Height | `10px` | ayni |
| Track | `rgba(247,238,222, 0.75)` | `rgba(28,46,40, 0.75)` |
| Thumb | `gradient(#5b4824 35%, #f7ce86 60%)` | `gradient(#4ADE80 35%, #22C55E 60%)` |
| Thumb Border | `2px solid rgba(247,238,222, 0.95)` | `rgba(28,46,40, 0.95)` |

### Kompakt Scrollbar (`.custom-scrollbar`)

| Ozellik | Light | Dark |
|---------|-------|------|
| Width | `6px` | ayni |
| Track | `transparent` | ayni |
| Thumb | `rgba(91,72,36, 0.2)` | `rgba(74,222,128, 0.15)` |

### Selection (`::selection`)

| Ozellik | Light | Dark |
|---------|-------|------|
| Background | `rgba(247,206,134, 0.4)` | `rgba(74,222,128, 0.3)` |
| Color | `#3a2d14` | `#F0FDF4` |

---

## 7. Responsive Tasarim

### Border Radius
| Eleman | Desktop | Mobile (<768px) |
|--------|---------|-----------------|
| Kartlar | `14px` | `12px` |
| Butonlar/Input | `0.875rem` | ayni |
| Badge | `999px` (pill) | ayni |

### Sidebar
| Durum | Genislik |
|-------|----------|
| Collapsed | `72px` |
| Expanded | `w-72` (288px) |
| Mobile | Overlay |

### Yaygin Padding Olcekleri
```
p-3 md:p-4
p-4 md:p-6
p-4 md:p-8
px-4 md:px-8
```

### Yaygin Text Olcekleri
```
text-sm md:text-base
text-xl md:text-2xl
text-2xl sm:text-3xl
```

---

## 8. Opacity / Alpha Kaliplari

Uygulama genelinde kullanilan standart opacity degerleri:

| Deger | Kullanim |
|-------|----------|
| `/5` | Cok hafif bg tint |
| `/8` | Hafif border, hover |
| `/10` | Alert bg, badge bg |
| `/12` | Input border, subtle border |
| `/15` | Border, surface-border |
| `/20` | Active state bg, stronger border |
| `/25` | Surface-border-strong |
| `/30` | Badge border, alert border |
| `/50` | Disabled state |

---

## 9. Kontrast Referansi (Dark Mode)

| Onplan | Arkaplan | Oran | WCAG |
|--------|----------|------|------|
| `#022c22` text | `#4ADE80` bg (accent buton) | 8.7:1 | AAA |
| `#F0FDF4` text | `#0F1A17` bg (sayfa) | 15.8:1 | AAA |
| `#A7C4B8` text | `#0F1A17` bg (sayfa) | 8.2:1 | AAA |
| `#6B8F80` text | `#0F1A17` bg (sayfa) | 4.5:1 | AA |
| `#6B8F80` text | `#162420` bg (kart) | 3.4:1 | AA (large) |
| `#4ADE80` text | `#0F1A17` bg (link) | 8.3:1 | AAA |

---

## 10. Bilinen Sorunlar ve Notlar

1. **`@theme` blogu zorunlu** — Tailwind v4'te `--color-*` degiskenleri `@theme` blogunda tanimlanmadigi surece utility class'lar (`bg-accent-primary`, `text-danger` vb.) **uretilmez**. `:root` blogu sadece runtime CSS variable saglar, Tailwind utility uretmez.

2. **Cift tanim** — `tailwind.config.js`'deki renkler ile `@theme` blogundaki renkler cakisabilir. Tailwind v4'te `@theme` once gelir; `tailwind.config.js` Tailwind v3 uyumluluk icin kalabilir ama tek kaynak `@theme` olmali.

3. **Hardcoded hex degerler** — TSX dosyalarinda `dark:text-[#F0FDF4]`, `bg-[#f7eede]` gibi arbitrary value'lar yaygin. Bunlar tema degiskenlerine baglanmadigi icin global tema degisikligi yapildiginda tek tek guncellenmeli.

4. **`.btn-primary` dark rengi** — `color: #022c22` (green-950). Accent butonlardaki `dark:text-[#022c22]` ile tutarli.
