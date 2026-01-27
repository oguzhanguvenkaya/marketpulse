# Proje Planı: Pazaryeri Veri Analiz Platformu

**Doküman:** 05 - Bütçe, Maliyet ve Kaynaklar Planı
**Tarih:** 10 Aralık 2025
**Versiyon:** 1.0

---

## 1. Faz 1 Bütçesi ve Aylık Giderler

Faz 1 (MVP) için öngörülen aylık operasyonel giderler, seçilen hibrit stratejiye (Bright Data + Playwright) ve orta seviye kullanıma göre hesaplanmıştır.

### Aylık Sabit Giderler

| Kalem | Hizmet Sağlayıcı | Tahmini Aylık Maliyet | Açıklama |
| :--- | :--- | :--- | :--- |
| **Sunucu (Server)** | DigitalOcean (Droplet) / AWS (EC2) | ~$30 | Backend, frontend ve veritabanını barındırmak için temel bir sanal sunucu. |
| **Yönetilen Veritabanı** | DigitalOcean / AWS RDS | ~$20 | PostgreSQL veritabanının kurulum, bakım ve yedekleme işlemlerini otomatize etmek için. |
| **Toplam Sabit Gider** | | **~$50 / ay** | |

### Aylık Değişken Giderler (Kullanıma Bağlı)

| Kalem | Hizmet Sağlayıcı | Tahmini Aylık Maliyet | Açıklama |
| :--- | :--- | :--- | :--- |
| **Proxy Hizmeti** | Bright Data (Residential) | ~$30 | 500 kelime x 100 ürün = 50,000 ürünün haftalık güncellenmesi varsayımıyla. |
| **LLM API Kullanımı** | OpenAI (GPT-4-Mini) | ~$30 | Aylık ortalama 100-150 CSV/Excel analizi yapılması varsayımıyla. |
| **Toplam Değişken Gider**| | **~$60 / ay** | |

### Toplam Faz 1 Aylık Maliyeti

**Toplam Tahmini Aylık Gider = Sabit Giderler + Değişken Giderler = $50 + $60 = ~$110 / ay**

Bu bütçe, projenin ilk aşaması için oldukça erişilebilir bir başlangıç noktası sunmaktadır. Kullanıcı sayısı ve veri hacmi arttıkça bu maliyetler ölçeklenecektir.

## 2. Gerekli İnsan Kaynakları ve Roller

Projenin Faz 1'i, yetenek setleri birbirini tamamlayan 2-3 kişilik çekirdek bir ekip tarafından başarıyla tamamlanabilir. İdeal ekip yapısı aşağıdaki rolleri içermelidir.

| Rol | Sorumluluk Alanları | Gerekli Yetenekler |
| :--- | :--- | :--- |
| **Full-Stack Geliştirici (Lider)** | Projenin genel teknik liderliği, backend ve frontend geliştirmesi, mimari kararlar. | Python (FastAPI), React, TypeScript, SQL, Docker. |
| **Backend & Veri Mühendisi** | Scraping altyapısı, veri işleme pipeline'ları, veritabanı yönetimi, LLM entegrasyonu. | Python, Playwright, BeautifulSoup, PostgreSQL, Celery, Redis. |
| **DevOps & Altyapı Mühendisi** | Sunucu kurulumu, CI/CD, deployment, monitoring, güvenlik ve yedekleme. | AWS/DigitalOcean, Docker, Nginx, Linux Sistem Yönetimi. |

**Not:** Projenin başlangıcında, tecrübeli bir Full-Stack Geliştirici, bu rollerin büyük bir kısmını tek başına üstlenebilir. Ekip, proje büyüdükçe ve uzmanlık gerektiren alanlar arttıkça genişletilebilir.

## 3. Riskler ve Karşı Önlemler

Her projede olduğu gibi, bu projede de potansiyel riskler bulunmaktadır. Bu risklerin önceden tespit edilmesi ve karşı önlemlerin planlanması, projenin başarısı için kritiktir.

| Risk Kategorisi | Potansiyel Risk | Etkisi | Olasılığı | Karşı Önlem |
| :--- | :--- | :--- | :--- | :--- |
| **Teknik Riskler** | Pazaryerlerinin HTML yapısını sık sık değiştirmesi. | Yüksek | Yüksek | Parser (ayrıştırıcı) script'lerini modüler tasarlamak, değişikliklere hızla adapte olabilmek için birim testleri yazmak. |
| | Bright Data'nın IP'lerinin pazaryerleri tarafından engellenmesi. | Yüksek | Düşük | Bright Data'nın sunduğu farklı proxy türlerini (ISP, Mobil) denemek, gerekirse ScrapingBee gibi alternatif bir servise geçiş planı hazırlamak. |
| **Maliyet Riskleri** | Beklenenden çok daha yoğun kullanım nedeniyle proxy ve API maliyetlerinin fırlaması. | Orta | Orta | Kullanıcılara limitler (rate limiting) koymak, maliyetleri anlık olarak izleyen bir dashboard oluşturmak, pay-as-you-go modelini korumak. |
| **Kaynak Riskleri** | Çekirdek ekip üyesinin projeden ayrılması. | Yüksek | Düşük | Kodun ve altyapının detaylı bir şekilde dokümante edilmesi, bilgi silolarını önlemek için düzenli kod incelemeleri (code review) yapmak. |
| **Pazar Riskleri** | Benzer bir rakip ürünün daha hızlı veya daha ucuza piyasaya çıkması. | Orta | Orta | Hızlı bir MVP (Minimum Viable Product) ile pazara ilk girenlerden olmak, kullanıcı geri bildirimlerine göre ürünü sürekli iyileştirerek rekabet avantajı sağlamak. |
