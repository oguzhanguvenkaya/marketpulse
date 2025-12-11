import os
import re
import json
import random
from datetime import date
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page
from playwright_stealth import Stealth
from app.core.config import settings
from app.services.proxy_providers import proxy_manager, debug_logger, ProxyProvider

stealth = Stealth()

MAX_PRODUCTS_PER_SEARCH = 8
MAX_RETRIES = 2

class ScrapingService:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.context = None
        self.current_provider: Optional[ProxyProvider] = None
        self.current_provider_name: str = "direct"
    
    async def init_browser(self, provider_name: Optional[str] = None, premium: bool = False):
        self.playwright = await async_playwright().start()
        
        if provider_name:
            provider = proxy_manager.get_provider(provider_name)
        else:
            provider = proxy_manager.get_primary_provider()
        
        self.current_provider = provider
        self.current_provider_name = provider.name if provider else "direct"
        
        proxy_config = provider.get_proxy_config(premium) if provider else None
        
        if proxy_config:
            print(f"Launching browser with {self.current_provider_name.upper()} proxy...")
            print(f"Proxy server: {proxy_config['server']}")
            print(f"Proxy username: {proxy_config['username'][:50]}...")
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                proxy=proxy_config
            )
            print(f"Browser launched with {self.current_provider_name} proxy!")
        else:
            print("No proxy configured, using direct connection")
            self.browser = await self.playwright.chromium.launch(headless=True)
        
        self.context = await self.browser.new_context(
            ignore_https_errors=True,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='tr-TR',
            timezone_id='Europe/Istanbul',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'max-age=0',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        return self.browser
    
    async def close_browser(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def reinit_with_fallback(self) -> bool:
        await self.close_browser()
        
        fallback = proxy_manager.get_fallback_provider(self.current_provider_name)
        if fallback:
            print(f"Switching to fallback provider: {fallback.name}")
            await self.init_browser(fallback.name)
            return True
        
        print("No fallback provider available")
        return False
    
    async def scrape_hepsiburada_search(self, keyword: str, max_products: int = MAX_PRODUCTS_PER_SEARCH) -> List[Dict[str, Any]]:
        if not self.browser:
            await self.init_browser()
        
        product_urls = await self._get_product_urls_from_search(keyword, max_products)
        
        if len(product_urls) == 0 and self.current_provider_name != "brightdata":
            print(f"No products found with {self.current_provider_name}, trying fallback...")
            if await self.reinit_with_fallback():
                product_urls = await self._get_product_urls_from_search(keyword, max_products)
        
        print(f"Found {len(product_urls)} product URLs to scrape")
        
        products = []
        for i, url in enumerate(product_urls[:max_products]):
            print(f"Scraping product {i+1}/{len(product_urls[:max_products])}: {url[:80]}...")
            try:
                product_data = await self.scrape_product_detail_page(url)
                if product_data:
                    products.append(product_data)
                    print(f"  -> Successfully scraped: {product_data.get('name', 'Unknown')[:50]}")
                await self._random_delay(1000, 3000)
            except Exception as e:
                debug_logger.log_error(url, self.current_provider_name, e)
                continue
        
        print(f"Successfully scraped {len(products)} products with full details")
        return products
    
    async def _get_product_urls_from_search(self, keyword: str, max_products: int) -> List[str]:
        page = await self.context.new_page()
        await stealth.apply_stealth_async(page)
        await self._apply_anti_detection(page)
        
        urls = []
        search_url = f"https://www.hepsiburada.com/ara?q={keyword.replace(' ', '+')}"
        
        try:
            print(f"Fetching search results: {search_url}")
            print(f"Using provider: {self.current_provider_name}")
            
            response = await page.goto(search_url, timeout=90000, wait_until="domcontentloaded")
            status = response.status if response else 0
            print(f"Search page response: {status}")
            
            debug_logger.log_request(search_url, self.current_provider_name, status)
            
            if status in [403, 429, 503]:
                content = await page.content()
                debug_logger.save_debug_html(search_url, content, status, self.current_provider_name)
                print(f"ERROR: Received {status} status - possible bot detection or rate limiting")
                return []
            
            await self._random_delay(3000, 5000)
            await self._simulate_human_behavior(page)
            
            content = await page.content()
            
            if "captcha" in content.lower() or "robot" in content.lower():
                debug_logger.save_debug_html(search_url, content, status, self.current_provider_name)
                print("WARNING: CAPTCHA or robot detection detected!")
                return []
            
            soup = BeautifulSoup(content, 'html.parser')
            
            product_links = soup.select('a[href*="-pm-"], a[href*="-p-"]')
            seen_urls = set()
            
            for link in product_links:
                href = link.get('href', '')
                if href and ('-pm-' in href or '-p-' in href):
                    if href.startswith('/'):
                        full_url = f"https://www.hepsiburada.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    base_url = full_url.split('?')[0]
                    if base_url not in seen_urls:
                        seen_urls.add(base_url)
                        urls.append(base_url)
                        
                        if len(urls) >= max_products:
                            break
            
            print(f"Extracted {len(urls)} unique product URLs from search")
            
            if len(urls) > 0:
                debug_logger.log_request(search_url, self.current_provider_name, status, f"Found {len(urls)} products")
            else:
                debug_logger.save_debug_html(search_url, content, status, self.current_provider_name)
            
        except Exception as e:
            debug_logger.log_error(search_url, self.current_provider_name, e)
            import traceback
            traceback.print_exc()
        finally:
            await page.close()
        
        return urls
    
    async def scrape_product_detail_page(self, url: str) -> Optional[Dict[str, Any]]:
        page = await self.context.new_page()
        await stealth.apply_stealth_async(page)
        await self._apply_anti_detection(page)
        
        try:
            response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            status = response.status if response else 0
            
            debug_logger.log_request(url, self.current_provider_name, status)
            
            if status not in [200, 301, 302]:
                print(f"Bad response for {url}: {status}")
                content = await page.content()
                debug_logger.save_debug_html(url, content, status, self.current_provider_name)
                return None
            
            await self._random_delay(2000, 4000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            utag_data = self._extract_utag_data(content)
            json_ld_data = self._extract_json_ld_data(soup)
            
            product_data = {
                "platform": "hepsiburada",
                "url": url,
                "external_id": self._extract_external_id(url),
            }
            
            if utag_data:
                product_data.update(self._parse_utag_data(utag_data))
            
            if json_ld_data:
                product_data.update(self._parse_json_ld_data(json_ld_data))
            
            html_data = self._extract_html_data(soup)
            product_data.update(html_data)
            
            product_data['other_sellers'] = self._extract_other_sellers(soup)
            product_data['reviews'] = self._extract_reviews(soup)
            product_data['coupons'] = self._extract_coupons(soup)
            product_data['campaigns'] = self._extract_campaigns(soup)
            
            return product_data
            
        except Exception as e:
            debug_logger.log_error(url, self.current_provider_name, e)
            import traceback
            traceback.print_exc()
            return None
        finally:
            await page.close()
    
    def _extract_external_id(self, url: str) -> str:
        match = re.search(r'-pm?-(\w+)', url)
        if match:
            return match.group(1)
        return url.split('/')[-1]
    
    def _extract_utag_data(self, html_content: str) -> Optional[Dict]:
        try:
            match = re.search(r'const\s+utagData\s*=\s*(\{[^;]+\});', html_content)
            if match:
                json_str = match.group(1)
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                return json.loads(json_str)
        except Exception as e:
            print(f"Error extracting utagData: {e}")
        return None
    
    def _extract_json_ld_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        try:
            scripts = soup.select('script[type="application/ld+json"]')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'Product':
                                return item
                    elif isinstance(data, dict):
                        if data.get('@type') == 'Product':
                            return data
                except:
                    continue
        except Exception as e:
            print(f"Error extracting JSON-LD: {e}")
        return None
    
    def _parse_utag_data(self, utag: Dict) -> Dict[str, Any]:
        data = {}
        
        if 'product_name_array' in utag:
            data['name'] = utag['product_name_array']
        elif 'product_names' in utag and utag['product_names']:
            data['name'] = utag['product_names'][0] if isinstance(utag['product_names'], list) else utag['product_names']
        
        if 'product_brand' in utag:
            data['brand'] = utag['product_brand']
        elif 'product_brands' in utag and utag['product_brands']:
            data['brand'] = utag['product_brands'][0] if isinstance(utag['product_brands'], list) else utag['product_brands']
        
        if 'merchant_names' in utag and utag['merchant_names']:
            data['seller_name'] = utag['merchant_names'][0] if isinstance(utag['merchant_names'], list) else utag['merchant_names']
        
        if 'category_name_hierarchy' in utag:
            data['category_hierarchy'] = utag['category_name_hierarchy']
        
        if 'category_path' in utag:
            data['category_path'] = utag['category_path']
        
        if 'product_barcode' in utag:
            data['barcode'] = utag['product_barcode']
        elif 'product_barcodes' in utag and utag['product_barcodes']:
            data['barcode'] = utag['product_barcodes'][0]
        
        if 'product_skus' in utag and utag['product_skus']:
            data['sku'] = utag['product_skus'][0]
        
        if 'product_status' in utag:
            data['in_stock'] = utag['product_status'].lower() == 'instock'
        
        if 'review_rate' in utag:
            try:
                rating_str = str(utag['review_rate']).replace(',', '.')
                data['rating'] = float(rating_str)
            except:
                pass
        
        if 'review_count' in utag:
            try:
                data['reviews_count'] = int(str(utag['review_count']).replace('.', ''))
            except:
                pass
        
        if 'product_prices' in utag and utag['product_prices']:
            try:
                price_str = str(utag['product_prices'][0]).replace('.', '').replace(',', '.')
                data['price'] = float(price_str)
            except:
                pass
        
        return data
    
    def _parse_json_ld_data(self, json_ld: Dict) -> Dict[str, Any]:
        data = {}
        
        if 'name' in json_ld and 'name' not in data:
            data['name'] = json_ld['name']
        
        if 'description' in json_ld:
            data['description'] = json_ld['description']
        
        if 'sku' in json_ld:
            data['sku'] = json_ld['sku']
        
        if 'gtin' in json_ld:
            data['barcode'] = json_ld['gtin']
        
        if 'brand' in json_ld:
            brand = json_ld['brand']
            if isinstance(brand, dict):
                data['brand'] = brand.get('name', '')
            else:
                data['brand'] = str(brand)
        
        if 'aggregateRating' in json_ld:
            rating = json_ld['aggregateRating']
            if 'ratingValue' in rating:
                data['rating'] = float(rating['ratingValue'])
            if 'ratingCount' in rating:
                data['reviews_count'] = int(rating['ratingCount'])
        
        if 'image' in json_ld:
            img = json_ld['image']
            if isinstance(img, list):
                data['image_url'] = img[0] if img else None
            else:
                data['image_url'] = img
        
        return data
    
    def _extract_html_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data = {}
        
        price_elem = soup.select_one('[data-test-id="price-current-price"]')
        if not price_elem:
            price_elem = soup.select_one('[class*="currentPrice"]')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            try:
                price_str = re.sub(r'[^\d,.]', '', price_text).replace('.', '').replace(',', '.')
                if price_str:
                    data['price'] = float(price_str)
            except:
                pass
        
        discounted_elem = soup.select_one('[class*="discountedPrice"]')
        if not discounted_elem:
            campaign_price = soup.find(string=re.compile(r'Sepete özel fiyat'))
            if campaign_price:
                parent = campaign_price.find_parent()
                if parent:
                    price_match = re.search(r'[\d.]+,\d+', parent.get_text())
                    if price_match:
                        try:
                            price_str = price_match.group().replace('.', '').replace(',', '.')
                            data['discounted_price'] = float(price_str)
                        except:
                            pass
        
        stock_elem = soup.find(string=re.compile(r'Stok Adedi'))
        if stock_elem:
            parent = stock_elem.find_parent()
            if parent:
                next_elem = parent.find_next_sibling() or parent.find_next()
                if next_elem:
                    stock_text = next_elem.get_text(strip=True)
                    match = re.search(r'(\d+)', stock_text)
                    if match:
                        data['stock_count'] = int(match.group(1))
                    elif 'az' in stock_text.lower():
                        data['stock_count'] = 50
        
        origin_elem = soup.find(string=re.compile(r'Menşei'))
        if origin_elem:
            parent = origin_elem.find_parent()
            if parent:
                next_elem = parent.find_next_sibling() or parent.find_next()
                if next_elem:
                    data['origin_country'] = next_elem.get_text(strip=True)
        
        desc_elem = soup.select_one('[class*="productDescription"]')
        if not desc_elem:
            desc_elem = soup.select_one('[data-test-id="product-description"]')
        if desc_elem:
            data['description'] = desc_elem.get_text(strip=True)[:5000]
        
        img_elem = soup.select_one('[class*="product-image"] img') or soup.select_one('[data-test-id="product-image"] img')
        if not img_elem:
            img_elem = soup.select_one('img[src*="productimages"]')
        if img_elem:
            data['image_url'] = img_elem.get('src') or img_elem.get('data-src')
        
        seller_rating_elem = soup.select_one('[class*="sellerRating"]')
        if not seller_rating_elem:
            seller_rating_text = soup.find(string=re.compile(r'\d+[,\.]\d+\s*Satıcı puanı'))
            if seller_rating_text:
                match = re.search(r'(\d+[,\.]\d+)', seller_rating_text)
                if match:
                    try:
                        data['seller_rating'] = float(match.group(1).replace(',', '.'))
                    except:
                        pass
        
        return data
    
    def _extract_other_sellers(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        sellers = []
        
        seller_section = soup.select('[class*="otherSeller"], [data-test-id*="other-seller"]')
        if not seller_section:
            seller_links = soup.select('a[href*="/magaza/"]')
            seen_sellers = set()
            
            for link in seller_links:
                seller_name = link.get_text(strip=True)
                if seller_name and seller_name not in seen_sellers and len(seller_name) < 100:
                    seen_sellers.add(seller_name)
                    
                    parent = link.find_parent('div') or link.find_parent('li')
                    seller_data = {
                        'seller_name': seller_name,
                        'is_authorized': 'yetkili' in str(parent).lower() if parent else False
                    }
                    
                    if parent:
                        price_elem = parent.select_one('[class*="price"]')
                        if price_elem:
                            price_text = price_elem.get_text(strip=True)
                            match = re.search(r'[\d.]+,\d+', price_text)
                            if match:
                                try:
                                    seller_data['price'] = float(match.group().replace('.', '').replace(',', '.'))
                                except:
                                    pass
                        
                        rating_match = re.search(r'(\d+[,\.]\d+)', parent.get_text())
                        if rating_match:
                            try:
                                seller_data['seller_rating'] = float(rating_match.group(1).replace(',', '.'))
                            except:
                                pass
                    
                    if len(sellers) < 10:
                        sellers.append(seller_data)
        
        return sellers
    
    def _extract_reviews(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        reviews = []
        
        review_cards = soup.select('[class*="reviewCard"], [data-test-id*="review"]')
        
        if not review_cards:
            json_ld_scripts = soup.select('script[type="application/ld+json"]')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'Review':
                                review = {
                                    'author': item.get('author', 'Anonim'),
                                    'rating': item.get('reviewRating', {}).get('ratingValue'),
                                    'review_text': item.get('reviewBody', ''),
                                    'review_date': item.get('datePublished')
                                }
                                reviews.append(review)
                except:
                    continue
        
        return reviews[:20]
    
    def _extract_coupons(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        coupons = []
        
        coupon_section = soup.select('[class*="coupon"], [data-test-id*="coupon"]')
        if not coupon_section:
            coupon_text = soup.find(string=re.compile(r'Kupon'))
            if coupon_text:
                parent = coupon_text.find_parent('div')
                if parent:
                    amount_match = re.search(r'(\d+)\s*TL', parent.get_text())
                    limit_match = re.search(r'Alt limit[:\s]*(\d+)', parent.get_text())
                    
                    coupon = {}
                    if amount_match:
                        coupon['amount'] = int(amount_match.group(1))
                    if limit_match:
                        coupon['min_order'] = int(limit_match.group(1))
                    
                    if coupon:
                        coupons.append(coupon)
        
        return coupons
    
    def _extract_campaigns(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        campaigns = []
        
        campaign_links = soup.select('a[href*="/kampanyalar/"]')
        seen = set()
        
        for link in campaign_links:
            text = link.get_text(strip=True)
            if text and text not in seen and len(text) > 5:
                seen.add(text)
                campaigns.append({
                    'name': text,
                    'url': link.get('href', '')
                })
        
        return campaigns[:5]
    
    async def _apply_anti_detection(self, page: Page):
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['tr-TR', 'tr', 'en-US', 'en']
            });
            window.chrome = {
                runtime: {}
            };
        """)
    
    async def _simulate_human_behavior(self, page: Page):
        try:
            await page.mouse.move(random.randint(100, 500), random.randint(100, 300))
            await self._random_delay(200, 500)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            await self._random_delay(500, 1000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        except:
            pass
    
    async def _random_delay(self, min_ms: int, max_ms: int):
        import asyncio
        delay = random.randint(min_ms, max_ms)
        await asyncio.sleep(delay / 1000)


def get_proxy_status() -> Dict[str, Any]:
    providers = proxy_manager.get_available_providers()
    primary = proxy_manager.get_primary_provider()
    
    return {
        "providers": providers,
        "primary_provider": primary.name if primary else "none",
        "debug_enabled": settings.DEBUG_SAVE_HTML,
        "debug_path": settings.DEBUG_HTML_PATH
    }
