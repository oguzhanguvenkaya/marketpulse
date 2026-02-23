# UI/UX Dark Theme Renk İncelemesi

- Tarih: 23 Şubat 2026
- İncelenen ortam: `http://localhost:5001/`
- İncelenen sayfalar: `/` (Dashboard), `/products`
- Görünümler: Desktop + Mobile

## 1) İnceleme Özeti

Dark theme görsel olarak aktive olmuş durumda olsa da, metin renklerinin önemli bir kısmı dark moda doğru şekilde geçmediği için ciddi okunabilirlik/kontrast problemleri oluşuyor. Bu nedenle renk paletinin genel uyumu ikinci planda kalıyor; asıl problem kontrastın sistematik olarak düşmesi.

Kısa sonuç:

- Evet, UX açısından kötü/çakışan renk kombinasyonları var.
- Evet, okunabilirlikte belirgin sorunlar var.
- Renkler bazı bileşenlerde birbiriyle uyumlu görünse de, metin-kontrast problemi genel deneyimi bozuyor.

## 2) Kullanılan Yöntem

Değerlendirme iki katmanda yapıldı:

1. Görsel inceleme:
- Dashboard ve Products sayfaları desktop/mobile görünümlerinde incelendi.
- Başlıklar, yan menü, kart içerikleri, liste/metadata metinleri ve rozet/butonlar karşılaştırıldı.

2. Programatik kontrast kontrolü:
- Görünür metin öğeleri üzerinden metin-arka plan kontrast oranı ölçüldü.
- WCAG eşikleri referans alındı:
  - Normal metin: en az `4.5:1`
  - Büyük metin: en az `3.0:1`

## 3) Nicel Bulgular (Kontrast)

- Toplam ölçülen görünür metin öğesi: `91`
- Eşiği geçemeyen öğe: `67`
- Başarısızlık oranı: yaklaşık `%73.6`

Örnek düşük kontrast değerleri:

- `Dashboard` başlığı: `1.04`
- `MarketPulse` marka metni: `1.2`
- Sidebar `Dashboard` etiketi: `1.2`
- `Keyword Search` başlığı: `1.3`
- `Recent Searches` başlığı: `1.3`
- `149` (metrik sayısı): `1.64`

Görece iyi örnekler:

- `Search` butonu metni: `~8.55`
- `completed` rozeti: `~6.22`
- `running` rozeti: `~6.58`

Yorum:

- Bazı accent/badge alanları iyi kontrast verirken, sayfanın ana bilgi taşıyan metinleri düşük kontrasta düşüyor.
- Bu dağılım, sorunun tekil değil sistematik bir tema uygulanma problemi olduğunu gösteriyor.

## 4) Görsel/UX Problemleri

### 4.1 Kritik okunabilirlik kaybı

- Koyu arka plan üzerinde başlık ve gövde metinleri fazla koyu kalıyor.
- Hiyerarşi bozuluyor: başlıklar, alt metinler ve yardımcı bilgiler birbirinden yeterince ayrışmıyor.
- Kullanıcı, tarama (scan) davranışında daha fazla efor harcıyor.

### 4.2 Bilgi önceliği bozulması

- Kart başlıkları, liste öğeleri ve metadata metinleri düşük kontrast yüzünden geri plana düşüyor.
- Buna karşılık bazı rozet/butonlar daha görünür kaldığı için bilgi mimarisi tersine dönüyor (ikincil öğe daha baskın, birincil içerik daha zayıf).

### 4.3 Mobilde etkinin artması

- Küçük font boyutlarında düşük kontrast etkisi daha da büyüyor.
- Özellikle sıkışık kart/liste düzenlerinde okunabilirlik kaybı daha erken hissediliyor.

## 5) Teknik Kök Neden Analizi

Tespit edilen davranış:

- Tema toggle ile `html` üzerinde `dark` class’ı aktif.
- Ancak birçok `dark:*` utility beklenen şekilde devreye girmiyor.
- Buna rağmen `.dark .card-dark` gibi özel selector’lar çalıştığı için arka planlar koyulaşıyor.
- Sonuç: Koyu arka plan + açık moda yakın metin renkleri => düşük kontrast.

Kök nedenin teknik özeti:

- Tailwind v4 çıktısında `dark:*` kurallarının class yerine `prefers-color-scheme: dark` medya sorgusuna bağlandığı gözlendi.
- Sistem teması light olduğunda (`prefers-color-scheme: dark = false`) bu kurallar uygulanmıyor.
- Uygulama ise class tabanlı dark mode toggle kullanıyor.
- Yani tema stratejisi ile derlenen varyant stratejisi arasında uyumsuzluk var.

İlgili dosyalar:

- `/Users/projectx/Desktop/marketpulse/frontend/package.json`
- `/Users/projectx/Desktop/marketpulse/frontend/src/index.css`
- `/Users/projectx/Desktop/marketpulse/frontend/tailwind.config.js`
- `/Users/projectx/Desktop/marketpulse/frontend/postcss.config.js`

Ek teknik not:

- Konsolda ayrıca `GET /api/stats/trends` için `404` hatası görüldü. Bu hata renk/tema probleminin ana sebebi değil, fakat dashboard bütünlüğünü etkileyebilir.

## 6) Renk Uyumu Değerlendirmesi

Palet tamamen uyumsuz değil; kötü algının ana nedeni hue çakışması değil, kontrastın kırılması.

- Uyumlu taraf:
  - Accent yeşil tonları ve status rozetleri kendi içinde daha tutarlı.
- Sorunlu taraf:
  - Nötr yüzeyler (dark background) ile metin tonları arasında luminance farkı yetersiz.
  - Başlık/gövde/yardımcı metin katmanları arasında tonal ayrım zayıf.

Sonuç:

- “Renkler birbirleri ile uyumlu mu?” sorusuna cevap: Kısmen.
- “Okunabilir mi?” sorusuna cevap: Birçok kritik alanda hayır.

## 7) Önceliklendirilmiş Düzeltme Planı

### P1 - Dark varyant stratejisini tekilleştir

- Class tabanlı dark mode kullanılacaksa `dark:*` varyantlarının class’a bağlanması garanti edilmeli.
- Amaç: `html.dark` aktif olduğunda tüm dark utility’lerin tutarlı şekilde devreye girmesi.

### P1 - Metin tokenlarını güçlendir

- Özellikle şu katmanlar için ayrı, net kontrast hedefi tanımla:
  - `text-primary` (ana içerik)
  - `text-secondary` (ikincil bilgi)
  - `text-muted` (yardımcı metadata)
- Dark yüzeylerde bu tokenları WCAG AA eşiğine göre kalibre et.

### P2 - Bileşen bazlı kontrast denetimi

- Dashboard card header/body, sidebar item, table/list row ve form yardımcı metinleri için kontrast checklist oluştur.
- Görsel olarak “iyi duruyor” yerine ölçülebilir eşiklerle doğrula.

### P2 - Mobil özel ayar

- Küçük fontlarda kontrastı bir adım daha artır (aynı renk değil, daha açık ton).
- Özellikle 12-14px bandında metinler için daha yüksek luminance farkı kullan.

## 8) Kabul Kriterleri (Doğrulama)

Renk düzeltmeleri tamamlandı sayılmadan önce:

1. `html.dark` açıkken kritik metinlerin tamamı kontrast eşiğini geçmeli.
2. Başarısız metin oranı `67/91` seviyesinden anlamlı şekilde düşmeli (hedef: kritik içerikte `0` fail).
3. Desktop ve mobile için aynı kontrast kuralları doğrulanmalı.
4. Dashboard + Products sayfalarında başlık, gövde ve metadata katmanları görsel hiyerarşi açısından ayrışmalı.

## 9) Kanıt / Ekran Görüntüleri

- `/Users/projectx/Desktop/marketpulse/output/playwright/ui-review/dashboard-dark-desktop.png`
- `/Users/projectx/Desktop/marketpulse/output/playwright/ui-review/dashboard-dark-mobile.png`
- `/Users/projectx/Desktop/marketpulse/output/playwright/ui-review/dashboard-light-desktop.png`
- `/Users/projectx/Desktop/marketpulse/output/playwright/ui-review/dashboard-desktop.png`

---

Bu rapor, mevcut durumda dark theme’in “aktif görünmesine rağmen” metin renklerinin büyük kısmında erişilebilirlik ve okunabilirlik standardını karşılamadığını doğrular.
