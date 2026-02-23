Renk Sistemi
Ana Renkler:

Token	Hex	Kullanım
--bg-primary	#0F1A17	Sidebar, ana arka plan
--bg-secondary	#162420	Kart arka planı, panel
--bg-tertiary	#1C2E28	Hover state, aktif sekme
--bg-surface	#243832	Input, dropdown, tablo satırı
--bg-elevated	#2A4039	Modal, tooltip, popup
Accent Renkler:

Token	Hex	Kullanım
--accent-primary	#4ADE80	CTA buton, aktif link, seçili tab — ana vurgu
--accent-primary-hover	#22C55E	Buton hover
--accent-secondary	#86EFAC	Badge, tag, hafif vurgu
--accent-muted	#4ADE8020	Seçili satır arka planı (opacity)
Metin Renkleri:

Token	Hex	Kullanım
--text-primary	#F0FDF4	Ana metin, başlıklar
--text-secondary	#A7C4B8	Alt başlık, açıklama
--text-muted	#6B8F80	Placeholder, devre dışı
--text-on-accent	#052E16	Accent buton üstündeki metin
Durum Renkleri:

Token	Hex	Kullanım
--success	#4ADE80	Başarılı, artış
--warning	#FBBF24	Uyarı, dikkat
--danger	#F87171	Hata, düşüş
--info	#38BDF8	Bilgi, link
Border / Separator:

Token	Hex
--border-default	#2A4039
--border-subtle	#1C2E28
--border-accent	#4ADE8040
Tipografi
Rol	Font	Ağırlık	Boyut
Heading (H1-H3)	Archivo	600-700	28/24/20px
Body	Inter	400-500	14-15px
Monospace (veri)	JetBrains Mono	400	13px
Tablo header	Inter	600	12px uppercase
Archivo başlıklarda geometrik, güçlü bir his verir. Inter gövde metinde okunabilirlik sağlar. JetBrains Mono fiyat, SKU, barcode gibi verilerde teknik his katar.

Komponent Örnekleri
Sidebar:

Arka plan: --bg-primary (#0F1A17)
Aktif menü: Sol kenarında 2px --accent-primary border + --bg-tertiary arka plan
İkon: --text-muted, aktif olunca --accent-primary
Ayırıcı çizgi: --border-subtle
Kartlar (Stat Card):

Arka plan: --bg-secondary
Border: 1px --border-default
Border radius: 12px
Başlık: --text-secondary, 12px uppercase
Değer: --text-primary, 24px bold
Değişim badge: yeşil (+) veya kırmızı (-), --accent-muted arka plan
Tablolar:

Header: --bg-surface, --text-secondary, 12px uppercase
Satır: --bg-secondary, hover'da --bg-tertiary
Zebra: Her 2. satır --bg-surface ile hafif ayrım
Border: Sadece yatay, --border-subtle
Butonlar:

Primary: --accent-primary arka plan, --text-on-accent metin, hover'da --accent-primary-hover
Secondary: Transparent, 1px --accent-primary border, --accent-primary metin
Danger: --danger arka plan, beyaz metin
Disabled: --bg-surface, --text-muted
Border radius: 8px
Input / Select:

Arka plan: --bg-surface
Border: 1px --border-default, focus'ta --accent-primary
Placeholder: --text-muted
Text: --text-primary
Badge / Tag:

Success: #4ADE8020 arka plan, #4ADE80 metin
Warning: #FBBF2420 arka plan, #FBBF24 metin
Danger: #F8717120 arka plan, #F87171 metin
Grafik Renkleri (Plotly / Chart)
Chart 1: #4ADE80  (yeşil — primary)
Chart 2: #38BDF8  (mavi)
Chart 3: #FBBF24  (sarı)
Chart 4: #F87171  (kırmızı)
Chart 5: #A78BFA  (mor)
Chart 6: #FB923C  (turuncu)
Koyu arka plan üzerinde bu renkler çok canlı ve okunabilir olur.

Mevcut Honey Teması ile Karşılaştırma
Özellik	Honey (Mevcut)	Forest Data (Yeni)
Mod	Light	Dark
Background	Krem (#fffbef)	Koyu yeşil (#0F1A17)
Primary	Kahverengi (#5b4824)	Yeşil accent (#4ADE80)
Accent	Altın (#f7ce86)	Lime (#4ADE80)
Hissi	Sıcak, organik	Premium, teknik, veri odaklı
Göz yorgunluğu	Gündüz iyi	Uzun süreli kullanımda daha rahat
Veri okunabilirliği	Orta	Yüksek (koyu bg + canlı accent)
Uygulama Kapsamı
Bu tema değişikliği şunları kapsar:

CSS değişkenleri / Tailwind config güncellemesi
Layout.tsx (sidebar, header)
14 sayfa bileşeninin renk token'larına geçirilmesi
Grafik renk paleti güncellemesi
Input, buton, kart, tablo, badge komponentleri
Mevcut Honey'den Forest'a geçiş yapısal olarak aynı pattern — CSS değişkenlerini değiştirmek yeterli olacak, komponent yapısı aynı kalır.