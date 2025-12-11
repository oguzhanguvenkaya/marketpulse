# ScraperAPI Proxy Port Metodu

**Kaynak:** https://docs.scraperapi.com/making-requests/proxy-port-method

## Temel Bilgiler

ScraperAPI, mevcut proxy altyapısı olan kullanıcılar için bir **proxy front-end** sunar. Bu proxy, istekleri alır ve API'ye iletir. API, proxy rotasyonu, CAPTCHA çözme ve yeniden deneme işlemlerini otomatik olarak halleder.

**Proxy Bilgileri:**
- **Host:** `proxy-server.scraperapi.com`
- **Port:** `8001`
- **Username:** `scraperapi`
- **Password:** `YOUR_API_KEY`

## Temel Kullanım (cURL Örneği)

```bash
curl -x "http://scraperapi:APIKEY@proxy-server.scraperapi.com:8001" -k "http://httpbin.org/ip"
```

**Önemli Not:** SSL sertifikalarının doğrulanmaması gerekir (`-k` bayrağı).

## Parametreler ile Kullanım

Ek işlevsellik için parametreler, username'e **nokta (.)** ile ayrılarak eklenebilir.

### JavaScript Rendering Örneği:

```bash
curl -x "http://scraperapi.render=true:APIKEY@proxy-server.scraperapi.com:8001" -k "http://httpbin.org/ip"
```

### Birden Fazla Parametre Örneği:

```bash
curl -x "http://scraperapi.render=true.country_code=us:APIKEY@proxy-server.scraperapi.com:8001" -k "http://httpbin.org/ip"
```

## Premium Residential Proxy Kullanımı

Premium (residential) proxy'ler için `premium=true` parametresi eklenir:

```bash
curl -x "http://scraperapi.premium=true.country_code=tr:APIKEY@proxy-server.scraperapi.com:8001" -k "https://www.hepsiburada.com/ara?q=laptop"
```

## Python ile Kullanım (Playwright)

```python
from playwright.sync_api import sync_playwright

SCRAPER_API_KEY = "YOUR_API_KEY"

proxy_config = {
    "server": "http://proxy-server.scraperapi.com:8001",
    "username": "scraperapi.premium=true.country_code=tr",
    "password": SCRAPER_API_KEY
}

with sync_playwright() as p:
    browser = p.chromium.launch(proxy=proxy_config)
    page = browser.new_page()
    page.goto("https://www.hepsiburada.com/ara?q=laptop")
    content = page.content()
    print(content)
    browser.close()
```

## Kullanılabilir Parametreler

| Parametre | Açıklama | Örnek |
|-----------|----------|-------|
| `render=true` | JavaScript rendering'i etkinleştirir | `scraperapi.render=true` |
| `premium=true` | Premium residential proxy kullanır | `scraperapi.premium=true` |
| `country_code=XX` | Belirli ülkeden IP kullanır | `scraperapi.country_code=tr` |
| `session_number=123` | Session stickiness sağlar | `scraperapi.session_number=123` |
| `keep_headers=true` | Özel header'ları korur | `scraperapi.keep_headers=true` |

## SSL Doğrulama ile Kullanım

Eğer SSL doğrulaması yapmak isterseniz, ScraperAPI'nin CA sertifikasını indirip sisteminize kurmanız gerekir.

### Windows:
1. MMC (Microsoft Management Console) açın
2. Certificates snap-in ekleyin
3. Trusted Root Certification Authorities'e sertifikayı import edin

### macOS:
1. Keychain Access açın
2. System tab'ında sertifikayı import edin
3. "Always Trust" olarak işaretleyin

### Linux:
```bash
sudo cp proxyca.pem /usr/local/share/ca-certificates/proxyca.pem
sudo update-ca-certificates
```

## Önemli Notlar

1. **SSL Doğrulama:** Varsayılan olarak SSL sertifikası doğrulaması devre dışı bırakılmalıdır
2. **Parametre Formatı:** Parametreler nokta (.) ile ayrılır: `scraperapi.param1=value1.param2=value2`
3. **Kredi Maliyeti:** Premium proxy kullanımı standart isteklerden 10 kat daha fazla kredi harcar
4. **Playwright Uyumluluğu:** Proxy port metodu Playwright ile **uyumludur** (API endpoint metodundan farklı olarak)
