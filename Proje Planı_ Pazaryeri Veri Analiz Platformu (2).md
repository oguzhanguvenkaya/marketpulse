# Proje Planı: Pazaryeri Veri Analiz Platformu

**Doküman:** 04 - Faz 2-3 Yol Haritası ve Uzun Vadeli Plan
**Tarih:** 10 Aralık 2025
**Versiyon:** 1.0

---

## 1. Uzun Vadeli Vizyon

Pazaryeri Veri Analiz Platformu, Türkiye'deki pazar liderliğinden sonra, küresel pazaryerlerini de kapsayacak şekilde genişleyerek, her ölçekteki e-ticaret satıcısı için vazgeçilmez bir "büyüme motoru" haline gelecektir. Platform, sadece veri sağlamakla kalmayıp, makine öğrenmesi ve yapay zeka ile proaktif olarak fırsatları tespit eden ve otomasyon ile satıcıların iş yükünü hafifleten bir asistana dönüşecektir.

## 2. Faz 2: Genişleme ve Derinleşme (2-4 Ay)

Faz 1'de kurulan temel altyapının üzerine, platformun yeteneklerini hem daha fazla pazaryerini kapsayacak şekilde genişletmek hem de analiz yeteneklerini derinleştirmek bu fazın ana hedefidir.

### Faz 2 Ana Hedefleri

-   **Pazaryeri Desteğini Artırma:** Trendyol ve Amazon Türkiye entegrasyonlarını tamamlamak.
-   **Satış Hacmi Tahmin Modeli:** Rakiplerin satış adetlerini tahmin eden bir model geliştirmek.
-   **Gelişmiş Rakip Analizi:** Rakiplerin en çok satan ürünlerini, fiyatlandırma geçmişini ve kampanya stratejilerini takip etmek.
-   **Kullanıcı Deneyimini İyileştirme:** Kullanıcı geri bildirimlerine göre arayüzde ve iş akışlarında iyileştirmeler yapmak.

### Faz 2 Teknik Geliştirmeleri

| Özellik | Açıklama | Teknik Detaylar |
| :--- | :--- | :--- |
| **Trendyol & Amazon Entegrasyonu** | Hepsiburada için geliştirilen scraping altyapısını diğer platformlara uyarlamak. | Her platform için ayrı parser (ayrıştırıcı) script'leri yazılacak. Veritabanı şeması `platform` sütunu ile bu ayrımı desteklemektedir. |
| **Satış Hacmi Tahmin Modeli** | Ürünlerin yorum sayısı, puanı, BSR (Best Seller Rank) gibi metrikleri kullanarak aylık satış hacmini tahmin eden bir makine öğrenmesi modeli. | Python (Scikit-learn, XGBoost) ile bir regresyon modeli eğitilecek. Model, periyodik olarak toplanan snapshot verilerini kullanacak. |
| **Fiyat Geçmişi Takibi** | Ürünlerin fiyat değişimlerini zaman içinde görselleştiren bir grafik. | `product_snapshots` tablosundaki veriler kullanılarak Plotly ile zaman serisi grafikleri oluşturulacak. |
| **Gelişmiş Filtreleme ve Sıralama** | Ürün listelerini fiyata, puana, yorum sayısına ve satış tahminine göre sıralama ve filtreleme. | Backend API'sine ve frontend arayüzüne yeni filtreleme parametreleri eklenecek. |

## 3. Faz 3: Akıllı Otomasyon ve Küresel Açılım (4+ Ay)

Bu fazda platform, reaktif bir analiz aracından, proaktif bir strateji asistanına dönüşecektir. Ayrıca, uluslararası pazaryerlerine açılarak küresel bir oyuncu olma yolunda ilk adımlar atılacaktır.

### Faz 3 Ana Hedefleri

-   **Trend Tespiti ve Fırsat Analizi:** Semrush/Ahrefs gibi SEO araçları ile entegrasyon sağlayarak yükselen trendleri önceden tespit etmek.
-   **Reklam Optimizasyon Önerileri:** Kullanıcının reklam verilerini ve pazar verilerini birleştirerek, hangi anahtar kelimelere ne kadar bütçe ayrılması gerektiği konusunda öneriler sunmak.
-   **Bildirim ve Uyarı Sistemi:** Takip edilen bir ürünün fiyatı düştüğünde veya bir rakip yeni bir kampanya başlattığında kullanıcıyı bilgilendirmek.
-   **Uluslararası Pazaryerleri:** Amazon ABD ve Avrupa gibi büyük pazarlara yönelik ilk entegrasyonları başlatmak.

### Faz 3 Teknik Geliştirmeleri

| Özellik | Açıklama | Teknik Detaylar |
| :--- | :--- | :--- |
| **SEO Araçları Entegrasyonu** | Semrush/Ahrefs API'lerini kullanarak anahtar kelime arama hacmi ve rekabet verilerini çekmek. | İlgili API'ler için yeni bir servis oluşturulacak ve bu veriler anahtar kelime analiz ekranına eklenecek. |
| **Negatif Anahtar Kelime Önerisi** | Düşük dönüşümlü veya alakasız reklam harcamalarını tespit ederek negatif kelime listeleri önermek. | LLM Analiz Servisi, reklam raporlarını analiz ederek bu önerileri üretecek. |
| **E-posta/Push Bildirimleri** | Kullanıcının belirlediği kurallara göre (örn: "Fiyat %10 düşünce haber ver") bildirim gönderen bir sistem. | Celery ile periyodik olarak kuralları kontrol eden bir görev ve e-posta/push notification servisi (örn: SendGrid, OneSignal) entegrasyonu. |
| **Çoklu Dil ve Para Birimi Desteği** | Arayüzü ve veri gösterimini farklı diller ve para birimlerine uygun hale getirmek. | Frontend'e i18n (internationalization) kütüphaneleri eklenecek. Backend, para birimi dönüşümleri için bir API kullanacak. |

## 4. Uzun Vadeli Gelecek (Post-Faz 3)

-   **Tam Otomasyon:** Kullanıcının onayı ile reklam kampanyalarını (bütçe artırma/azaltma, yeni kelime ekleme) otomatik olarak yönetme.
-   **Tedarik Zinciri Entegrasyonu:** Satış tahminlerine göre stok seviyelerini optimize etmek için envanter yönetimi araçlarıyla entegrasyon.
-   **Kişiselleştirilmiş Pazar Raporları:** Her satıcının kendi ürün portföyüne özel, yapay zeka tarafından üretilen haftalık pazar ve rekabet raporları.
-   **API Erişimi:** Gelişmiş kullanıcıların ve ajansların, platformun verilerini kendi araçlarına entegre etmeleri için bir genel API sunma.
