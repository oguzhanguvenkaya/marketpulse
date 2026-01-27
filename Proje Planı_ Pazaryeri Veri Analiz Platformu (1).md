# Proje Planı: Pazaryeri Veri Analiz Platformu

**Doküman:** 03 - Faz 1 Uygulama Planı ve Görev Dağılımı
**Tarih:** 10 Aralık 2025
**Versiyon:** 1.0

---

## 1. Faz 1 Hedefi

Pazaryeri Veri Analiz Platformu'nun, temel özellikleri barındıran, çalışır bir Minimum Viable Product (MVP) versiyonunu 4-5 hafta içinde hayata geçirmek. Bu MVP, Hepsiburada platformuna odaklanacak ve kullanıcının temel veri toplama ve analiz ihtiyaçlarını karşılayacaktır.

## 2. Faz 1 Kapsamındaki Ana Özellikler (Features)

1.  **Anahtar Kelime Arama:** Kullanıcının belirlediği bir anahtar kelime için Hepsiburada arama sonuçlarındaki ilk 100 ürünü listeleme.
2.  **Ürün Detay Sayfası:** Listelenen bir ürünün tüm detaylarını (fiyat, puan, yorum, açıklama, satıcı vb.) ayrı bir sayfada gösterme.
3.  **Satıcı Analizi:** Bir satıcının mağazasındaki ürünleri, en çok kullandığı kelimeleri ve kategori dağılımını analiz etme.
4.  **CSV/Excel Veri Analizi:** Kullanıcının yüklediği reklam verisi dosyasını LLM kullanarak otomatik analiz etme, görselleştirme ve öneri sunma.
5.  **Hibrit Veri Güncelleme Stratejisi:**
    -   **İlk Veri Alımı:** Bright Data ile güvenilir şekilde yapılır.
    -   **Periyodik Güncelleme:** Maliyeti düşürmek için önce ücretsiz Playwright ile denenir, başarısız olanlar daha sonra Bright Data ile güncellenir.

## 3. Faz 1 Zaman Çizelgesi (Timeline)

Proje, 5 haftalık bir sprint planı ile yönetilecektir.

### Hafta 1: Kurulum ve Temel Altyapı

-   **Hedef:** Proje iskeletini oluşturmak ve temel araçları entegre etmek.
-   **Görevler:**
    -   Bright Data hesabı oluşturma ve proxy zone ayarlarını yapma.
    -   Proje klasör yapısını ve Git repository'sini oluşturma.
    -   Backend (FastAPI) ve Frontend (React) için temel iskeleti kurma.
    -   PostgreSQL veritabanı ve tabloları (schema) oluşturma.
    -   Playwright ile Bright Data proxy'sinin çalıştığını doğrulayan basit bir test script'i yazma.
-   **Çıktı:** Çalışan bir "Hello World" seviyesinde backend ve frontend, ayarlanmış veritabanı.

### Hafta 2: Çekirdek Scraping Mantığı

-   **Hedef:** Ana veri toplama özelliklerini geliştirmek.
-   **Görevler:**
    -   `Anahtar Kelime Arama` özelliğinin backend servisini yazma.
    -   `Ürün Detay Sayfası` scraping mantığını geliştirme.
    -   Veri doğrulama katmanını (Pydantic ile) implemente etme.
    -   Çekilen verileri PostgreSQL'e kaydetme mantığını oluşturma.
-   **Çıktı:** Belirlenen bir anahtar kelime için veri çekip veritabanına kaydeden API endpoint'leri.

### Hafta 3: Gelişmiş Özellikler ve Veri İşleme

-   **Hedef:** Analiz ve güncelleme özelliklerini eklemek.
-   **Görevler:**
    -   `Satıcı Analizi` özelliğinin backend servisini geliştirme.
    -   Hibrit veri güncelleme stratejisini (günlük/haftalık cron job'lar) implemente etme.
    -   `CSV/Excel Analizi` için dosya yükleme endpoint'ini ve LLM entegrasyonunu yapma.
    -   Celery ile asenkron görev altyapısını kurma.
-   **Çıktı:** Arka planda çalışan veri toplama ve analiz görevleri.

### Hafta 4: Arayüz (Frontend) Geliştirme ve Entegrasyon

-   **Hedef:** Kullanıcının verileri görebileceği ve etkileşime geçebileceği arayüzü oluşturmak.
-   **Görevler:**
    -   Kullanıcı dashboard'unu tasarlama ve kodlama.
    -   Arama, ürün listeleme ve detay sayfalarını oluşturma.
    -   Backend API'lerini frontend'e entegre etme.
    -   Plotly ile üretilen grafikleri arayüzde gösterme.
-   **Çıktı:** Backend ile konuşan, işlevsel bir kullanıcı arayüzü.

### Hafta 5: Test, Dağıtım (Deployment) ve İyileştirme

-   **Hedef:** Projeyi canlıya almak ve stabil çalışmasını sağlamak.
-   **Görevler:**
    -   Uçtan uca (end-to-end) testler yapma.
    -   Uygulamayı Docker ile konteyner haline getirme.
    -   Seçilen bulut sağlayıcısına (DigitalOcean, AWS vb.) deploy etme.
    -   Temel monitoring (izleme) ve logging (kayıt tutma) altyapısını kurma.
    -   Kullanıcı geri bildirimlerine göre küçük iyileştirmeler yapma.
-   **Çıktı:** Canlıda çalışan, erişilebilir bir MVP.

## 4. Görev Dağılımı (Task Breakdown)

Proje, 3 ana rolden oluşan küçük bir ekiple gerçekleştirilebilir.

### Backend Geliştirici Görevleri

-   API endpoint'lerini (FastAPI) tasarlama ve kodlama.
-   Veritabanı şemasını yönetme ve sorguları yazma (SQLAlchemy).
-   Scraping script'lerini (Playwright, BeautifulSoup) geliştirme.
-   Bright Data entegrasyonunu yapma.
-   Asenkron görevleri (Celery) yönetme.
-   LLM API entegrasyonunu yapma.
-   Birim ve entegrasyon testlerini yazma.

### Frontend Geliştirici Görevleri

-   Kullanıcı arayüzü bileşenlerini (React) kodlama.
-   Sayfa tasarımlarını (TailwindCSS) uygulama.
-   Backend API'leri ile veri alışverişini sağlama.
-   Veri görselleştirme kütüphanelerini (Plotly.js vb.) entegre etme.
-   Kullanıcı deneyimini (UX) iyileştirme.

### DevOps Mühendisi Görevleri

-   Sunucu altyapısını kurma ve yönetme (DigitalOcean, AWS).
-   CI/CD (Sürekli Entegrasyon/Dağıtım) pipeline'ını kurma (opsiyonel).
-   Uygulamayı Dockerize etme.
-   Veritabanı ve diğer servislerin kurulumunu ve bakımını yapma.
-   Monitoring ve logging sistemlerini kurma.
-   Güvenlik ve yedekleme stratejilerini uygulama.
