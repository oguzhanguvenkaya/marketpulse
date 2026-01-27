# ScraperAPI + Playwright Entegrasyon Notları

**Kaynak:** https://www.scraperapi.com/quick-start-guides/playwright/

## Önerilen Yöntem: API Endpoint Metodu

ScraperAPI ile Playwright'ı entegre etmenin en güvenilir yolu, **doğrudan ScraperAPI endpoint'ine istek göndermektir**.

### Temel Kullanım (Node.js Örneği)

```javascript
const { chromium } = require('playwright');
require('dotenv').config();

const SCRAPERAPI_KEY = process.env.SCRAPERAPI_KEY;
const targetUrl = 'http://httpbin.org/ip';
const scraperApiUrl = `http://api.scraperapi.com?api_key=${SCRAPERAPI_KEY}&url=${encodeURIComponent(targetUrl)}`;

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  await page.goto(scraperApiUrl, { waitUntil: 'domcontentloaded' });
  
  const content = await page.textContent('body');
  console.log('IP Details:', content);
  
  await browser.close();
})();
```

## Opsiyonel Parametreler

ScraperAPI, query parametreleri ile ek özellikler sunar:

- `render=true` – JavaScript rendering'i etkinleştirir
- `country_code=us` – Belirli bir ülkeden IP kullanır (örn: `country_code=tr` Türkiye için)
- `session_number=123` – Aynı proxy oturumunu kullanır (session stickiness)
- `premium=true` – Premium (residential) proxy'ler kullanır

### Premium Residential Proxy Örneği:

```javascript
const scraperApiUrl = `http://api.scraperapi.com?api_key=${SCRAPERAPI_KEY}&premium=true&country_code=tr&url=${encodeURIComponent(targetUrl)}`;
```

## ÖNERİLMEYEN Yöntem: Proxy Mode

ScraperAPI'nin proxy port'unu (`proxy-server.scraperapi.com:8001`) doğrudan Playwright'ın `launch()` seçeneklerinde kullanmak **başarısız olur**.

### Neden Başarısız Olur?

- ScraperAPI, API anahtarının query parametresi olarak gönderilmesini gerektirir
- Playwright'ın proxy yapılandırması Basic Auth veya IP auth bekler, query string'leri desteklemez
- Sonuç: `Proxy Authentication Required` hatası

## Python İçin Uyarlama

Python'da Playwright ile ScraperAPI kullanımı:

```python
from playwright.sync_api import sync_playwright
import os

SCRAPERAPI_KEY = os.getenv('SCRAPER_API_KEY')
target_url = 'https://www.hepsiburada.com/ara?q=laptop'
scraper_api_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&premium=true&country_code=tr&url={target_url}"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(scraper_api_url)
    content = page.content()
    print(content)
    browser.close()
```

## Best Practices

1. **API anahtarını `.env` dosyasında sakla** (güvenlik için)
2. **JavaScript-yoğun siteler için `render=true` kullan**
3. **ScraperAPI kullanırken Playwright proxy ayarlarından kaçın** (çakışma yaratır)
4. **Rate limit ve eşzamanlılık limitlerini gözet**
5. **Premium proxy kullanımı kredi maliyetini artırır** (genelde 10x)

## Önemli Notlar

- **Proxy Mode çalışmaz:** ScraperAPI'nin proxy port'u Playwright ile doğrudan uyumlu değildir
- **API Endpoint tercih edilir:** Hem daha güvenilir hem de test etmesi daha kolay
- **Kredi sistemi:** Premium istekler standart isteklerden 10 kat daha fazla kredi harcar
