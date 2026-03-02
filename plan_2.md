# MarketPulse — Eklenti Planı (Pro Modüller)

**Tarih:** 2026-02-26
**Bağlam:** Bu doküman, ana MVP planı olan `plan.md`'nin **üzerine inşa edilecek** olan ileri seviye "SaaS Büyüme ve Kârlılık" özelliklerini (Pro Modüller) listeler. `plan.md` dosyasındaki Faz 0, 1, 2 ve 3 standart fiyat takip ve basit otomasyon özelliklerini kapsarken; bu eklenti planı satıcının kârlılığını maksimize etmeyi ve müşteri hizmetleri operasyonunu otonomlaştırmayı hedefler.

---

## Eklenecek Yeni Özellikler (plan.md'de Olmayanlar)

Ana planda sadece "Fiyat Takibi ve Rakip Analizi" varken, bu eklenti planı şu dört büyük yeniliği getirir:
1.  **Kârlılık Simülasyonu:** Pazaryerindeki sabit komisyon oranları ve kullanıcının girdiği "sabit kargo tutarı" üzerinden ürün başı net kârın hesaplanması ("Satış 100 ₺ -> Maliyet 50 ₺ -> Komisyon 15 ₺ -> Kargo 90 ₺ = Zarar -55 ₺").
2.  **Kampanya Otomasyonu (Opportunity Hub):** Pazaryerindeki yeni kampanyaları çekip, kârlı olanlara otomatik (kırmızı çizgi kuralı ile) katılım sağlama.
3.  **Harici Botsuz (Botpress vb.) AI Müşteri Hizmetleri:** Backend içine entegre edilmiş Celery taskları ve doğrudan LLM çağrıları ile müşteri sorularını otomatik (veya taslak olarak) yanıtlama.
4.  **Category Analyzer & Reklam Optimizasyonu:** Bir ürünün bulunduğu kategorideki ilk 40 ürünü analiz edip "doğru kategoride" olup olmadığını denetleme ve pazar trendlerine (HB Rota vb.) göre yüksek getiri sağlayacak anahtar kelimeleri önerme.

---

## FAZ 4 — Kârlılık Yönetimi ve Kampanya Otomasyonu

> **Hedef:** Kullanıcı ekran başında değilken bile kârlılığını maksimize eden "Güvenlik Ağı" otomasyonları kurmak.

### 4.1 Kârlılık Simülatörü ve Şelale (Waterfall) Grafiği
**Efor:** 4-5 gün
- Sabit kategori komisyonlarını (örn: Elektronik %8) ve kullanıcının girdiği Ortalama Kargo Bedelini (`90 TL`) veritabanında tutma.
- Ürün detay sayfasında ve fiyat değiştirme anında net kârı simüle etme.
- Fiyat kırıldığında veya yeni kampanyaya girildiğinde net zarara geçiş durumlarında görsel uyarılar (UI) oluşturma.

### 4.2 Kampanya Fırsat Merkezi (Opportunity Hub)
**Efor:** 3-4 gün
- HB ve TY Promotions API'leri aracılığıyla aktif pazaryeri kampanyalarının sisteme çekilmesi ve listelenmesi.
- AI'ın kampanyalar için öneri sunması: *"Eğer X kampanyasına katılırsan Buybox'ı kazanırsın ve ürün başına net X TL kâr edersin."*

### 4.3 Kırmızı Çizgi Otomasyonu (Actionable Rules)
**Efor:** 5-7 gün
- Kullanıcının her ürüne veya mağazaya bir "Kırmızı Çizgi" (Min %15 Kâr Marjı) ataması.
- Fiyat savaşlarında veya kampanya fırsatlarında sistemin arka planda `dry-run` (önizleme) hesaplaması yapması.
- Şartlar uygunsa Promosyon API üzerinden kampanyaya otomatik kayıt; rakip kârın altına iniyorsa zararına satışı durdurmak için fiyat savaşından çekilme.

---

## FAZ 5 — Native AI Müşteri Hizmetleri (Dahili Asistan)

> **Hedef:** Botpress, Dialogflow gibi harici ve masraflı bot platformlarına sıfır bağımlılıkla tam 5 dakika içinde pazaryeri sorularına otonom yanıt vermek.

### 5.1 Bağlam Seti ve Polling Altyapısı
**Efor:** 3-4 gün
- `plan.md`'deki Celery yapısına eklenti olarak her 5 dakikada bir HB/TY Müşteri Soruları (Customer Questions) API'sinin çekilmesi.
- Gelen sorunun ilgili olduğu ürünün açıklamasının ve mağazanın statik politikalarının (kargo süresi, iade şartları) veritabanından Context (Bağlam) olarak derlenmesi.

### 5.2 AI Yanıt Üretimi ve Onay Akışı
**Efor:** 4-5 gün
- Hazırlanan verilerin GPT-4o-mini veya Claude-3-Haiku ile işlenerek yanıt üretilmesi.
- **Taslak (Copilot) Modu:** Cevabın Pano'ya onaya düşmesi ve kullanıcının "Onayla ve Gönder" veya "Düzenle" butonlarıyla PAZARYERİNE (API ile) iletmesi.
- **Autopilot Modu:** Güven seviyesi test edildikten sonra (opsiyonel), AI'ın yanıtı saniyeler içinde doğrudan pazaryeri API'si üzerinden göndermesi.

---

## FAZ 6 — Görünürlük, Reklam ve Kategori Optimizasyonu (SEO & Ads)

> **Hedef:** Hatalı kategorizasyon kaynaklı reklam (ROAS) çöplerini engellemek ve platform içi trend/rota verileriyle nokta atışı reklam kelimeleri önermek.

### 6.1 Category Analyzer (Kategori Uyumluluk Denetimi)
**Efor:** 4-5 gün
- **Sorun:** "Metal Polish" ürününü "Araç Kokusu" kategorisine koyan satıcı, o kategorideki kelimelere reklam çıkarsa dönüşüm alamaz (ROAS düşer).
- **Çözüm (Tek Tuşla Analiz):** Sistem, arka planda ürünün halihazırda listelendiği kategorideki ilk 40 ürünü (isim, fiyat, görsel, açıklama) çeker (Category Explorer modülü kullanılarak).
- **LLM Değerlendirmesi:** Yapay zeka, satıcının ürünü ile rakiplerin 40 ürününü karşılaştırır ve uyumluluk skoru üretir. *"Ürünün yanlış kategoride! Rakiplerin hepsi araç kokusu satıyor, sen cila satıyorsun. Reklam çıkmadan önce kategorini değiştir."*

### 6.2 Trend (Rota) Tabanlı Akıllı Reklam Kelimesi Önerisi
**Efor:** 3-4 gün
- **Sorun:** Pazaryerleri (özellikle HB Rota) kelime hacimlerini (Yüksek/Orta/Düşük) verir ancak satıcı hangi kelimiye reklam çıkacağını bilemez.
- **Çözüm:** HB Rota (veya TY Trend) verilerinin sisteme periyodik çekilmesi.
- **Aksiyon Önerisi:** *"X Kategorisindeki yıldızı 4.5 üstü olan ve Buybox'ı sağlam olan ürünün için 'Yüksek Hacimli' şu 3 kelimeye reklam çıkarsan getirisi (dönüşüm oranı) maksimum olur."* (Boşa tıklama maliyeti engellenir).

---

## Doğrulama Planı (Faz 4, Faz 5 ve Faz 6)

- [ ] Kârlılık grafiği, sabit kargo ve sabit komisyon ile net sonucu doğru veriyor.
- [ ] Zararına fiyat düşüşü (Kırmızı çizginin ihlali) simüle edildiğinde sistem görsel kırmızı uyarı çıkarıyor.
- [ ] Trendyol/HB API'den kampanya listesi başarıyla Çekiliyor (Opportunity Hub).
- [ ] Otomasyon kuralı: Kâr marjı sınırı içindeki kampanyaya ürün API aracılığıyla otonom katılabiliyor.
- [ ] Müşteri soruları Celery Beat ile içeriye başarılı olarak aktarılıyor.
- [ ] Native AI, ürün texti ve şirket politikası haricinde harici halüsinasyon yapmadan düzgün Taslak Metin üretebiliyor.
- [ ] Taslak onaylandığında cevap API üzerinden pazaryerine gidiyor.
- [ ] Category Analyzer, ürün ile kategorisindeki 40 rakibi karşılaştırıp doğru/yanlış kategori uyarısı verebiliyor.
- [ ] Trend kelimeler arasından yüksek yıldızlı/Buybox sahibi ürünlere özel reklam kelimesi eşleştirmesi yapılıyor.

---

## Efor Değişimi
`plan.md`'deki ana 13 haftalık MVP hedefine ek olarak, bu Pro Modüllerin sisteme eklenmesi projenin yaşam döngüsüne kabaca **4 ile 6 Hafta (25-35 İş Günü)** efor ekleyecektir. Bu özellikler MVP'yi izleyen aşamalarda veya Faz 2 ve 3 ile paralel kodlanabilir.
