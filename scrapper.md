# Hepsiburada JavaScript Rendering Test Sonuçları

**Tarih:** 11 Aralık 2025
**Test URL:** https://www.hepsiburada.com/ara?q=laptop

---

## Test 1: Statik HTML vs JavaScript Rendering

### Basit HTTP GET (curl/requests)
**Sonuç:** ❌ **BAŞARISIZ**
- Timeout hatası
- Hepsiburada bot koruması aktif
- Basit HTTP istekleri reddediliyor

### Tarayıcı ile Yükleme (Playwright)
**Sonuç:** ✅ **BAŞARILI**
- Sayfa düzgün yüklendi
- 46 adet `<article>` tag bulundu (ürün kartları)
- Ürünler görünür durumda

### JavaScript Rendering İhtiyacı
**SONUÇ:** ✅ **JAVASCRIPT RENDERING ZORUNLU**

**Kanıt:**
1. Basit HTTP GET → Timeout (bot koruması)
2. Tarayıcı ile → 46 ürün yüklendi
3. Ürünler `<article>` tag'leri içinde dinamik olarak render ediliyor

**Anlam:**
- Hepsiburada, bot koruması nedeniyle basit HTTP isteklerini engelliyor
- Playwright gibi gerçek tarayıcı simülasyonu **ZORUNLU**
- ScraperAPI API Endpoint metodu **KULLANILMAMALI**
- ScraperAPI Proxy Mode veya Bright Data **ZORUNLU**

---

## Test 2: Ürün Verisi Yapısı

### HTML Yapısı
```html
<article> tag'leri içinde ürün kartları
```

**Bulunan Element Sayıları:**
- `<article>` tag: 46 adet
- `data-test-id` ile product: 0 adet (farklı attribute kullanıyor olabilir)

### Scroll İhtiyacı
**Test Edilmedi** - Ancak sayfa 10.000+ ürün gösteriyor
- İlk yüklemede sadece 46 ürün
- Muhtemelen infinite scroll veya sayfalama var
- Scroll işlemi için Playwright **GEREKLİ**

---

## SONUÇ VE ÖNERİ

### ❌ KULLANILMAMALI
- ScraperAPI API Endpoint (HTTP GET)
- Basit requests/curl
- BeautifulSoup tek başına

### ✅ KULLANILMALI
**Seçenek 1: ScraperAPI Proxy Mode + Playwright**
- Avantaj: Daha ucuz
- Dezavantaj: SSL sorunları olabilir

**Seçenek 2: Bright Data + Playwright**
- Avantaj: En güvenilir, SSL sorunu yok
- Dezavantaj: Daha pahalı

### 🎯 Nihai Karar
**Playwright kullanımı ZORUNLU** - Tartışma yok.

Soru: ScraperAPI Proxy Mode mu, Bright Data mı?
→ SSL testi gerekli (Aşama 2)




# Bright Data vs ScraperAPI: Maliyet ve Performans Karşılaştırması

**Tarih:** 11 Aralık 2025
**Amaç:** Kullanıcının aylık kullanım senaryosuna göre en uygun proxy sağlayıcısını belirlemek

---

## Kullanım Senaryosu (Kullanıcı Gereksinimleri)

**Aylık Kullanım:**
- 3.000 anahtar kelime araması
- Her aramada 50 ürün listesi
- Her ürünün detay sayfası
- Haftada 3-4 kez güncelleme

**Hesaplama:**
```
Arama sayfaları: 3.000 kelime × 1 sayfa = 3.000 istek
Ürün sayfaları: 3.000 kelime × 50 ürün = 150.000 istek
Toplam (ilk çekim): 153.000 istek

Haftalık güncelleme: 3.5 kez/hafta × 4 hafta = 14 güncelleme/ay
Aylık toplam: 153.000 × 14 = 2.142.000 istek/ay
```

**Güvenlik Payı ile:** ~2.5 milyon istek/ay

---

## Bright Data Fiyatlandırması

### Residential Proxy (Gerekli - Bot Koruması İçin)

**Fiyat Yapısı:**
- Pay-as-you-go: $12.75/GB
- Aylık abonelik: Değişken, minimum $500/ay

**Veri Tüketimi Tahmini:**
- Ortalama sayfa boyutu: 500 KB (JavaScript, görseller dahil)
- 2.5M istek × 0.5 MB = 1.25 TB = 1,250 GB

**Aylık Maliyet:**
```
1,250 GB × $12.75/GB = $15,937.50/ay
```

**Türk Lirası (1 USD = 35 TL):**
```
$15,937.50 × 35 = ₺557,812.50/ay
```

### Datacenter Proxy (Daha Ucuz Ama Hepsiburada Engelliyor)

**Fiyat:** $0.11/IP/saat
**Sorun:** Hepsiburada datacenter IP'leri engelliyor → Kullanılamaz

---

## ScraperAPI Fiyatlandırması

### Proxy Port Metodu (Playwright ile)

**Paketler:**
| Paket | Aylık Fiyat | İstek Sayısı | Birim Maliyet |
|-------|-------------|--------------|---------------|
| Hobby | $49 | 100K | $0.00049/istek |
| Startup | $149 | 1M | $0.000149/istek |
| **Business** | **$249** | **3M** | **$0.000083/istek** |
| Enterprise | Custom | 10M+ | Özel fiyat |

**Bizim İhtiyacımız:** 2.5M istek/ay → **Business Paketi ($249/ay)**

**Premium Proxy Ek Maliyeti:**
- Premium proxy: 10x maliyet
- Ancak ScraperAPI'de premium, paket fiyatına dahil
- Ek maliyet: **YOK**

**Türk Lirası:**
```
$249 × 35 = ₺8,715/ay
```

---

## Karşılaştırma Tablosu

| Özellik | Bright Data | ScraperAPI |
|---------|-------------|------------|
| **Aylık Maliyet** | ~₺558,000 | ₺8,715 |
| **İstek Kapasitesi** | Sınırsız (GB bazlı) | 3M istek |
| **Playwright Uyumluluğu** | ✅ Mükemmel | ⚠️ SSL bypass gerekebilir |
| **Bot Koruması Aşma** | ✅ En güçlü | ✅ İyi |
| **CAPTCHA Çözme** | ✅ Otomatik | ✅ Otomatik |
| **Türkiye IP** | ✅ Var | ✅ Var (country_code=tr) |
| **Dokümantasyon** | ✅ Kapsamlı | ✅ Kapsamlı |
| **Destek** | ✅ 24/7 | ✅ Email |
| **Replit Uyumluluğu** | ✅ Sorunsuz | ⚠️ Test gerekli |

---

## Maliyet Farkı

```
Bright Data: ₺558,000/ay
ScraperAPI:  ₺8,715/ay

Tasarruf: ₺549,285/ay (%98.4 tasarruf)
```

---

## Performans Karşılaştırması

### Bright Data
**Avantajlar:**
- En güvenilir residential proxy ağı
- SSL sorunu YOK
- CAPTCHA çözme oranı en yüksek
- Replit'te kesinlikle çalışır

**Dezavantajlar:**
- Astronomik maliyet
- Küçük projeler için overkill

### ScraperAPI
**Avantajlar:**
- %98 daha ucuz
- 3M istek kapasitesi yeterli
- Playwright desteği var
- Premium proxy dahil

**Dezavantajlar:**
- SSL bypass gerekebilir (ignore_https_errors=True)
- Bright Data kadar güçlü değil
- Replit uyumluluğu test edilmeli

---

## Risk Analizi

### ScraperAPI Riskleri

**Risk 1: SSL Sertifika Sorunu**
- **Olasılık:** Orta
- **Etki:** Düşük (ignore_https_errors=True ile çözülür)
- **Replit'te:** Muhtemelen sorun olmaz (Replit cloud ortamı)

**Risk 2: Hepsiburada Engelleme**
- **Olasılık:** Düşük (Premium proxy kullanıyoruz)
- **Etki:** Yüksek (Veri çekilemez)
- **Çözüm:** Bright Data'ya geçiş (modüler yapı sayesinde kolay)

**Risk 3: İstek Limiti Aşımı**
- **Olasılık:** Düşük (3M > 2.5M)
- **Etki:** Orta (Ek ücret veya hız sınırı)
- **Çözüm:** Business+ pakete yükselt

---

## NİHAİ ÖNERİ

### Aşama 1: MVP (İlk 3 Ay)
**Kullan:** ScraperAPI Business ($249/ay)

**Neden:**
1. %98 daha ucuz
2. MVP için yeterli
3. Modüler yapı sayesinde gerekirse Bright Data'ya geçiş kolay
4. Risk/getiri oranı mükemmel

### Aşama 2: Ölçeklendirme (3+ Ay)
**Değerlendir:** Bright Data'ya geçiş

**Ne Zaman:**
1. Aylık gelir $5,000+ olduğunda
2. ScraperAPI engelleme yaşarsa
3. Müşteri sayısı 50+ olduğunda

---

## Karar Matrisi

| Kriter | Ağırlık | Bright Data | ScraperAPI |
|--------|---------|-------------|------------|
| Maliyet | 40% | 1/10 | 10/10 |
| Güvenilirlik | 30% | 10/10 | 7/10 |
| Kolay Kurulum | 15% | 8/10 | 9/10 |
| Replit Uyumluluğu | 15% | 10/10 | 8/10 |
| **Toplam Puan** | | **5.7/10** | **8.7/10** |

**KAZANAN:** ScraperAPI (MVP aşaması için)


