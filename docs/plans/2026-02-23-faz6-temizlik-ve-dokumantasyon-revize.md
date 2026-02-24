# Faz 6: Temizlik ve Dokümantasyon — Revize Ekip Planı

**Context:**
Faz 1-5'in başarıyla tamamlanmasının ardından, repoda biriken teknik borcun temizlenmesi gerekmektedir. Önceki analizlerde tespit edilen geniş çaplı "blast radius" riskini minimize etmek adına süreç birbirine bağımlı olmayan 3 Track'e (Aşama) bölünmüştür. Bu durum rollback (geri alma) stratejisini çok daha güvenli kılacaktır.

---

## 🛤️ TRACK 1: Backend Hygiene & Configuration (Backend Hijyeni ve Config)
**Öncelik:** Çok Yüksek | **Risk:** Düşük | **Tahmini Süre:** 1-2 Saat

Bu adım sadece backend logları, yapılandırma dosyaları ve reponun statik git durumunu doğrudan hedefler.

### 1.1 Repo Temizliği (Tracked Assets Untrack)
*   **Sorun:** `attached_assets/` (73MB) ve `hepsiburada_active_products.json` git geçmişinde yer alıyor. Bunlar `.gitignore` listesine dahil edilmeli ve repo temizlenmelidir.
*   **Aksiyon:**
    ```bash
    git rm --cached -r attached_assets/
    git rm --cached hepsiburada_active_products.json
    ```

### 1.2 Graceful Deprecation: `SCRAPPER` -> `SCRAPER_API_KEY`
*   **Sorun:** Kötü isimlendirilmiş environment değişkeleri anında silinirse canlı sistemler (replit/sunucu) çökebilir.
*   **Aksiyon:** `backend/app/core/config.py` içerisinde:
    *   Bir okuma (fallback) stratejisi yazılacak.
    *   Eğer ortam değişkenlerinde `SCRAPPER_API` dolu gelirse bir sistem log'u atılacak:
        `logger.warning("DEPRECATION WARNING: 'SCRAPPER_API' kullanımı durdurulacak. Lütfen ortam değişkenlerini 'SCRAPER_API_KEY' olarak güncelleyin.")`
    *   `transcript_service.py` ve sistem kodları yeni `settings.SCRAPER_API_KEY` tanımına yönlendirilecek.
    *   Değişken 1 tam release döngüsünün ardından (Faz 7'de) tamamen kaldırılacak.

### 1.3 `DEBUG_SAVE_HTML` Standardizasyonu
*   **Sorun:** Canlıda her HTML'in kaydedilmesi bellek sızıntısına ve yetersiz depolamaya yol acar. Default'un `True` bırakılması yanlıştır.
*   **Aksiyon:** Pydantic modelinde default değer `False` çekilecek.
*   **Operasyonel Belgeleme:** `DEPLOY.md` veya `DEBUG.md` dosyasına şu satır eklenecek:
    * *"Scraper debug'ı yapmak ve fail eden HTML'leri görmek için Production'da gecici olarak ortam değişkenlerine `DEBUG_SAVE_HTML=True` ekleyerek container'ı restart edin. Debug bitince mutlaka kapatın."*

### 1.4 `.env.example` Otomasyonu
*   **Sorun:** Manuel `.env` kopyalaması drift yaratır (uzun vadede geçerliliğini yitirir).
*   **Aksiyon:** Python'da ufak bir script (`scripts/generate_env_example.py`) yazılacak veya Pydantic BaseSettings'den doğrudan parse edilecek biçimde güncel key'leri placeholder değerlerle çıkaracak bir sistem kurulacak. Bu sayede dosya her dev/build işleminde senkronize olur.

---

## 🛤️ TRACK 2: Dependency & Security Update (Paket ve Güvenlik Güncellemeleri)
**Öncelik:** Yüksek | **Risk:** Orta | **Tahmini Süre:** 1 Saat

Npm ağacındaki CVE (güvenlik zafiyeti) barındıran paketlerin ve React ekosisteminin riskli varyasyonlarından kurtulması amaçlanır. Frontend kodunda **hiçbir business-logic değişikliği yapılmadan** izole uygulanıp test edilmelidir.

### 2.1 Güvenlik ve Minor Güncellemeler
*   **Aksiyon:** Sadece `minor` ve `patch` paket güncellemeleri yapılacak. (Major/Breaking update'ler - örneğin eslint 9->10 atlanacak).
    *   `react-router-dom`: 7.10.1 → 7.13.1 (3 CVE fix)
    *   `react` / `react-dom`: 19.2.1 → 19.2.4
    *   `vite`, `tailwindcss` ve `plotly.js` minor versiyon artışları.
*   **Test & Onay:**
    *   Network (ENOTFOUND) kısıtlamaları yüzünden komutlar CI pipeline'larında veya unrestricted development ortamında çalıştırılmalıdır:
    ```bash
    cd frontend && npm update && npm audit fix
    npm run build
    ```

---

## 🛤️ TRACK 3: Frontend Token Migration (Görsel ve UI Refactoring)
**Öncelik:** Yüksek | **Risk:** Yüksek | **Tahmini Süre:** 4-6 Saat

Arayüz geliştirmenin Tailwind V4 doğasına entegrasyonu, semantic token kullanımının tamamen projeye hakim olması.

### 3.1 CSS Theming Base'in Kurulumu
*   **Aksiyon:** `frontend/src/index.css` dosyasına Hex->Token eşleştirme tablosunda yer alan eksik renkler tanım olarak (theme variable) eklenecektir. (Örn: `--color-text-faded`, `--color-surface-hover` vb.)

### 3.2 3 Fazlı TSX Migrasyonu
*   **Büyük Resim:** Taramalara göre Frontend TSX klasöründe toplam **977 adet** (önceki verideki gibi 604 değil) `dark:` override tespiti bulunmaktadır. Amaç bu kirliliği 0'a yakınlaştırmak ve semantic renklere devretmektir.
*   **Yaklaşım:** Değerler 3 Batch'e bölünerek, her batch sonrası Visual / QA doğrulaması yapılacaktır.
    *   **Batch 1 (Küçük Etki):** ErrorBoundary, ConfirmDialog, DetayPaneller vb. 15 küçük dosya.
    *   **Batch 2 (Orta Etki):** Sidebar, Products, Ads, Layout vb. ana grid yapıları. 8 dosya.
    *   **Batch 3 (Büyük Etki):** JsonEditor, Sellers, ProductCards vb. en büyük bileşenlerin override satır satır incelenerek güncellenmesi.

### 3.3 Validasyon Kriterleri
*   Derleme esnasında tipik hataların oluşmadığı: `npx tsc --noEmit`
*   `grep -roh 'dark:' frontend/src/ --include="*.tsx" | wc -l` değerinin %90+ oranında azaldığının (margin-of-error hariç) doğrulanması.
*   Opacity class'larında tailwind config mix/rgb hatalarına yol açılmaması (örn `border-accent-primary/20` kullanımının render bozukluğu yaratmaması).

---
**Deployment Stratejisi:** Track 1, Track 2 ve Track 3 birbirinden ayrı Pull Request / Dev Branch süreçlerinde yürütülerek ana projeye (main) Merge edilmelidir. İşlem bitiminde `DEPLOY.md` tüm developer'lara dağıtılmalıdır.
