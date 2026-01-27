import os
import re
import json
import random
import asyncio
import aiohttp
from urllib.parse import quote_plus, unquote, urlparse, parse_qs
from datetime import date
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page
from playwright_stealth import Stealth
from app.core.config import settings
from app.core.logger import scraping_logger as logger
from app.services.proxy_providers import proxy_manager, debug_logger, ProxyProvider

stealth = Stealth()

MAX_PRODUCTS_PER_SEARCH = 8
MAX_RETRIES = 2

SCRAPERAPI_BASE_URL = "http://api.scraperapi.com"

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
            logger.info(f"Launching browser with {self.current_provider_name.upper()} proxy")
            logger.debug(f"Proxy server: {proxy_config['server']}")
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                proxy=proxy_config
            )
            logger.info(f"Browser launched with {self.current_provider_name} proxy")
        else:
            logger.info("No proxy configured, using direct connection")
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
    
    async def close_browser(self, reset_provider: bool = False):
        """Close browser and optionally reset provider state.
        
        Args:
            reset_provider: If True, reset provider info. Keep False when switching providers
                           so reinit_with_fallback can determine the next provider in chain.
        """
        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")
            self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            self.browser = None
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping playwright: {e}")
            self.playwright = None
        
        if reset_provider:
            self.current_provider = None
            self.current_provider_name = "direct"
    
    async def reinit_with_fallback(self) -> bool:
        await self.close_browser()
        
        fallback = proxy_manager.get_fallback_provider(self.current_provider_name)
        if fallback:
            logger.info(f"Switching to fallback provider: {fallback.name}")
            await self.init_browser(fallback.name)
            return True
        
        logger.warning("No fallback provider available")
        return False
    
    async def _fetch_with_scraperapi_proxy(self, url: str, session_number: int = 1, render_js: bool = False, wait_for_selector: str = None, premium: bool = True) -> Optional[str]:
        """Fetch URL using ScraperAPI proxy port method - WORKING for Hepsiburada
        
        Args:
            url: URL to fetch
            session_number: Session number for sticky session
            render_js: Enable JavaScript rendering (for dynamic content like "Sepete özel" prices)
            wait_for_selector: CSS selector to wait for before returning (requires render_js=True)
            premium: Use premium proxies for protected domains like Hepsiburada (default: True)
        """
        if not settings.SCRAPER_API_KEY:
            return None
        
        proxy_url = "http://proxy-server.scraperapi.com:8001"
        
        username_parts = [
            "scraperapi",
            "country_code=tr",
            "device_type=desktop",
            "max_cost=200",
            f"session_number={session_number}"
        ]
        
        if premium:
            username_parts.insert(1, "premium=true")
        
        if render_js:
            username_parts.insert(1, "render=true")
        
        proxy_username = ".".join(username_parts)
        
        logger.debug(f"ScraperAPI PROXY PORT request: {url[:60]}...")
        logger.debug(f"Using session_number: {session_number}, render_js: {render_js}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=180)
            
            connector = aiohttp.TCPConnector(ssl=False)
            
            auth = aiohttp.BasicAuth(
                login=proxy_username,
                password=settings.SCRAPER_API_KEY
            )
            
            headers = {}
            if render_js:
                headers['x-sapi-render'] = 'true'
                if wait_for_selector:
                    instruction_set = [
                        {
                            "type": "wait_for_selector",
                            "selector": {"type": "css", "value": wait_for_selector},
                            "timeout": 10
                        }
                    ]
                    headers['x-sapi-instruction_set'] = json.dumps(instruction_set)
                    logger.debug(f"Waiting for selector: {wait_for_selector}")
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(
                    url,
                    proxy=proxy_url,
                    proxy_auth=auth,
                    headers=headers if headers else None,
                    ssl=False
                ) as response:
                    status = response.status
                    logger.debug(f"ScraperAPI PROXY response status: {status}")
                    
                    debug_logger.log_request(url, "scraperapi-proxy", status)
                    
                    if status == 200:
                        html = await response.text()
                        logger.debug(f"ScraperAPI PROXY returned {len(html)} bytes")
                        return html
                    elif status in [403, 429, 500, 503]:
                        content = await response.text()
                        debug_logger.save_debug_html(url, content, status, "scraperapi-proxy")
                        logger.warning(f"ScraperAPI PROXY error {status}: {content[:200]}")
                        return None
                    else:
                        logger.warning(f"ScraperAPI PROXY unexpected status: {status}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"ScraperAPI PROXY timeout for {url[:60]}...")
            debug_logger.log_error(url, "scraperapi-proxy", Exception("Timeout"))
            return None
        except Exception as e:
            logger.error(f"ScraperAPI PROXY error: {e}")
            debug_logger.log_error(url, "scraperapi-proxy", e)
            return None
    
    async def _fetch_with_scraperapi(self, url: str, render: bool = True, premium: bool = False) -> Optional[str]:
        if not settings.SCRAPER_API_KEY:
            return None
        
        params = {
            "api_key": settings.SCRAPER_API_KEY,
            "url": url,
            "render": "true" if render else "false",
            "country_code": "tr",
            "device_type": "desktop",
        }
        
        if premium:
            params["premium"] = "true"
        
        api_url = f"{SCRAPERAPI_BASE_URL}?" + "&".join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
        
        logger.debug(f"ScraperAPI HTTP request: {url[:60]}...")
        
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url) as response:
                    status = response.status
                    logger.debug(f"ScraperAPI response status: {status}")
                    
                    debug_logger.log_request(url, "scraperapi", status)
                    
                    if status == 200:
                        html = await response.text()
                        logger.debug(f"ScraperAPI returned {len(html)} bytes")
                        return html
                    elif status in [403, 429, 500, 503]:
                        content = await response.text()
                        debug_logger.save_debug_html(url, content, status, "scraperapi")
                        logger.warning(f"ScraperAPI error {status}: {content[:200]}")
                        return None
                    else:
                        logger.warning(f"ScraperAPI unexpected status: {status}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"ScraperAPI timeout for {url[:60]}...")
            debug_logger.log_error(url, "scraperapi", Exception("Timeout"))
            return None
        except Exception as e:
            logger.error(f"ScraperAPI error: {e}")
            debug_logger.log_error(url, "scraperapi", e)
            return None
    
    def _extract_real_url_from_tracking(self, href: str) -> Optional[str]:
        """Extract real product URL from adservice tracking URL"""
        if 'adservice.' in href and 'redirect=' in href:
            try:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                if 'redirect' in params:
                    redirect_url = unquote(params['redirect'][0])
                    if '-p-' in redirect_url or '-pm-' in redirect_url:
                        return redirect_url.split('?')[0]
            except Exception as e:
                logger.debug(f"Error parsing tracking URL: {e}")
        return None
    
    def _extract_sponsored_brands_from_search(self, html: str) -> List[Dict[str, Any]]:
        """Extract brand carousel ads (AUTO POWER, MTS Kimya vb.) from search page with full product data"""
        sponsored_brands = []
        products_by_merchant = {}
        
        ad_info_pattern = r'"adInfo":"[^"]*".*?"merchantName":"([^"]+)".*?"merchantId":"([^"]+)".*?"listingId":"([^"]+)"'
        
        for match in re.finditer(ad_info_pattern, html, re.DOTALL):
            merchant_name, merchant_id, listing_id = match.groups()
            start_pos = match.start()
            end_pos = min(match.end() + 2000, len(html))
            context = html[start_pos:end_pos]
            
            product_data = {
                'price': None,
                'discounted_price': None,
                'name': None,
                'url': None,
                'image_url': None
            }
            
            price_match = re.search(r'"price":\s*([0-9.]+)', context)
            if price_match:
                product_data['price'] = self._parse_float(price_match.group(1))
            
            disc_patterns = [
                r'"discountedPrice":\s*([0-9.]+)',
                r'"salePrice":\s*([0-9.]+)',
                r'"discountPrice":\s*([0-9.]+)'
            ]
            for pattern in disc_patterns:
                disc_match = re.search(pattern, context)
                if disc_match:
                    product_data['discounted_price'] = self._parse_float(disc_match.group(1))
                    break
            
            name_patterns = [
                r'"productName":"([^"]+)"',
                r'"name":"([^"]+)"',
                r'"title":"([^"]+)"'
            ]
            for pattern in name_patterns:
                name_match = re.search(pattern, context)
                if name_match:
                    product_data['name'] = name_match.group(1)
                    break
            
            url_match = re.search(r'"url":"(/[^"]+)"', context)
            if url_match:
                product_data['url'] = f"https://www.hepsiburada.com{url_match.group(1)}"
            else:
                url_match = re.search(r'"url":"(https://[^"]+)"', context)
                if url_match:
                    product_data['url'] = url_match.group(1)
            
            img_patterns = [
                r'"imageUrl":"([^"]+)"',
                r'"image":"([^"]+)"',
                r'"productImage":"([^"]+)"',
                r'"images":\["([^"]+)"'
            ]
            for pattern in img_patterns:
                img_match = re.search(pattern, context)
                if img_match:
                    product_data['image_url'] = img_match.group(1)
                    break
            
            if merchant_id not in products_by_merchant:
                products_by_merchant[merchant_id] = {
                    'seller_name': merchant_name,
                    'seller_id': merchant_id,
                    'products': []
                }
            
            products_by_merchant[merchant_id]['products'].append(product_data)
        
        for idx, (merchant_id, brand_data) in enumerate(products_by_merchant.items(), start=1):
            sponsored_brands.append({
                'seller_name': brand_data['seller_name'],
                'seller_id': brand_data['seller_id'],
                'position': idx,
                'products': brand_data['products']
            })
        
        if sponsored_brands:
            total_products = sum(len(b['products']) for b in sponsored_brands)
            logger.info(f"Extracted {len(sponsored_brands)} brand ads with {total_products} total products")
        
        return sponsored_brands
    
    def _extract_sponsored_products_from_search(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract individual sponsored products (with Reklam badge) from search page with order info.
        
        Returns list of sponsored products with their display order (1-indexed position on page).
        """
        sponsored_products = []
        
        product_cards = soup.select('article[class*="productCard-module_article"]')
        if not product_cards:
            li_products = soup.find_all('li', class_=lambda x: x and 'productListContent' in str(x))
            product_cards = li_products
        
        for idx, card in enumerate(product_cards, start=1):
            card_str = str(card)
            is_sponsored = 'advertisement-module_adRoot' in card_str or 'adRoot' in card_str
            
            if not is_sponsored:
                continue
            
            link = card.select_one('a[href*="-p-"], a[href*="-pm-"]')
            if not link:
                link = card.find('a', href=lambda x: x and ('/p-' in x or '/pm-' in x))
            url = link.get('href') if link else None
            
            name = None
            h3 = card.find('h3')
            if h3:
                name = h3.get_text(strip=True)
            if not name:
                title_elem = card.find(attrs={'title': True})
                if title_elem:
                    name = title_elem.get('title')
            
            price = None
            discounted_price = None
            price_elem = card.select_one('[data-test-id="price-current-price"], [class*="price"]')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'([\d.]+,\d+)', price_text)
                if price_match:
                    price = self._parse_float(price_match.group(1).replace('.', '').replace(',', '.'))
            
            image_url = None
            img = card.select_one('img[src*="productimages"], img[data-src*="productimages"]')
            if img:
                image_url = img.get('src') or img.get('data-src')
            
            if url:
                if url.startswith('/'):
                    url = f"https://www.hepsiburada.com{url}"
                
                sponsored_products.append({
                    'order_index': idx,
                    'url': url.split('?')[0],
                    'name': name,
                    'price': price,
                    'discounted_price': discounted_price,
                    'image_url': image_url,
                    'is_sponsored': True
                })
        
        if sponsored_products:
            logger.info(f"Found {len(sponsored_products)} sponsored products at positions: {[p['order_index'] for p in sponsored_products]}")
        
        return sponsored_products
    
    def _extract_basket_campaign_prices(self, soup: BeautifulSoup) -> Dict[str, float]:
        """Extract discounted prices from basket campaign elements in search page.
        
        Returns dict mapping product URL -> discounted price
        """
        basket_prices = {}
        
        product_cards = soup.select('article[class*="productCard-module_article"]')
        
        for card in product_cards:
            basket_campaign = card.select_one('[class*="isBasketCampaign"]')
            if not basket_campaign:
                continue
            
            link = card.select_one('a[href*="-p-"], a[href*="-pm-"]')
            if not link:
                continue
            
            href = link.get('href', '')
            if href.startswith('/'):
                url = f"https://www.hepsiburada.com{href}".split('?')[0]
            elif href.startswith('https://'):
                url = href.split('?')[0]
            else:
                continue
            
            text = basket_campaign.get_text(strip=True)
            prices = re.findall(r'([\d.]+,\d+)\s*TL', text)
            
            if len(prices) >= 2:
                try:
                    discounted = float(prices[1].replace('.', '').replace(',', '.'))
                    basket_prices[url] = discounted
                except:
                    pass
            elif len(prices) == 1:
                try:
                    discounted = float(prices[0].replace('.', '').replace(',', '.'))
                    basket_prices[url] = discounted
                except:
                    pass
        
        if basket_prices:
            logger.info(f"Extracted {len(basket_prices)} basket campaign prices from search page")
        
        return basket_prices
    
    def _extract_product_urls_from_soup(self, soup: BeautifulSoup, max_products: int, sponsored_urls: set = None) -> List[str]:
        """Extract ORGANIC product URLs from search result page (excludes sponsored products).
        
        Args:
            soup: BeautifulSoup object of search page
            max_products: Maximum number of organic products to return
            sponsored_urls: Set of sponsored product URLs to exclude from count
        
        Returns:
            List of organic product URLs (up to max_products)
        """
        urls = []
        seen_urls = set()
        sponsored_urls = sponsored_urls or set()
        
        product_cards = soup.select('article[class*="productCard-module_article"]')
        
        if product_cards:
            logger.debug(f"Found {len(product_cards)} product cards via article selector")
            cards_with_links = []
            for card in product_cards:
                card_str = str(card)
                is_sponsored = 'advertisement-module_adRoot' in card_str or 'adRoot' in card_str
                links = card.select('a[href*="-p-"], a[href*="-pm-"]')
                if links:
                    cards_with_links.append((links[0], is_sponsored))
        else:
            product_links = soup.select('a[class*="productCardLink"][href*="-p-"], a[class*="productCardLink"][href*="-pm-"]')
            if product_links:
                logger.debug(f"Found {len(product_links)} product links via productCardLink selector")
            else:
                product_containers = soup.select('ul[class*="productListContent"], div[class*="productListContent"]')
                if product_containers:
                    for container in product_containers:
                        links = container.select('a[href*="-p-"], a[href*="-pm-"]')
                        product_links.extend(links)
                    logger.debug(f"Found {len(product_links)} links in {len(product_containers)} product containers")
                else:
                    product_links = soup.select('a[href*="-p-"], a[href*="-pm-"]')
                    logger.debug(f"Using fallback: found {len(product_links)} total product links")
            cards_with_links = [(link, False) for link in product_links]
        
        organic_count = 0
        sponsored_count = 0
        
        for link, is_card_sponsored in cards_with_links:
            href = link.get('href', '')
            if not href:
                continue
            
            full_url = None
            
            if 'adservice.' in href and 'redirect=' in href:
                full_url = self._extract_real_url_from_tracking(href)
            elif href.startswith('/'):
                if '-p-' in href or '-pm-' in href:
                    full_url = f"https://www.hepsiburada.com{href}"
            elif href.startswith('https://www.hepsiburada.com/'):
                if '-p-' in href or '-pm-' in href:
                    full_url = href
            
            if not full_url:
                continue
            
            if 'adservice.' in full_url or 'tracking.' in full_url or 'event/api' in full_url:
                continue
            
            if not full_url.startswith('https://www.hepsiburada.com/'):
                continue
            
            base_url = full_url.split('?')[0]
            
            if base_url in seen_urls:
                continue
            
            seen_urls.add(base_url)
            
            if is_card_sponsored or base_url in sponsored_urls:
                sponsored_count += 1
                continue
            
            urls.append(base_url)
            organic_count += 1
            
            if organic_count >= max_products:
                break
        
        logger.info(f"Extracted {len(urls)} organic product URLs (skipped {sponsored_count} sponsored)")
        
        return urls
    
    async def _get_product_urls_via_http_api(self, keyword: str, max_products: int) -> Dict[str, Any]:
        """Get product URLs using ScraperAPI PROXY PORT method - proven to work with Hepsiburada
        
        Returns dict with:
        - urls: List of product URLs to scrape
        - sponsored_brands: List of brand ads (AUTO POWER, MTS Kimya vb.)
        - sponsored_product_urls: Set of URLs that are sponsored
        """
        
        search_url = f"https://www.hepsiburada.com/ara?q={keyword.replace(' ', '+')}"
        logger.info(f"Fetching search results: {search_url[:60]}...")
        
        session_number = random.randint(1, 10000)
        html = await self._fetch_with_scraperapi_proxy(search_url, session_number=session_number)
        
        if html:
            soup_check = BeautifulSoup(html, 'html.parser')
            title = soup_check.find('title')
            title_text = title.get_text() if title else ""
            
            if "En Çok Tavsiye Edilen" in title_text or "Anasayfa" in title_text:
                logger.warning(f"Got homepage instead of search results (title: {title_text[:50]})")
                logger.info("Retrying with new session...")
                session_number = random.randint(10001, 20000)
                html = await self._fetch_with_scraperapi_proxy(search_url, session_number=session_number)
        
        if not html:
            logger.warning("ScraperAPI PROXY failed, trying Bright Data fallback...")
            self.current_provider_name = "brightdata"
            if self.browser:
                logger.debug("Closing existing browser before switching to Bright Data...")
                await self.close_browser()
            logger.info("Initializing Bright Data browser with Playwright...")
            await self.init_browser("brightdata")
            urls = await self._get_product_urls_from_search(keyword, max_products)
            return {'urls': urls, 'sponsored_brands': [], 'sponsored_product_urls': set()}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find('title')
        title_text = title.get_text() if title else "No title"
        logger.debug(f"Page title: {title_text[:80]}")
        
        if settings.DEBUG_SAVE_HTML:
            import os
            debug_dir = "/tmp/scraping_debug"
            os.makedirs(debug_dir, exist_ok=True)
            debug_file = f"{debug_dir}/search_{keyword.replace(' ', '_')}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.debug(f"Saved search HTML to {debug_file}")
        
        sponsored_brands = self._extract_sponsored_brands_from_search(html)
        
        sponsored_products = self._extract_sponsored_products_from_search(soup)
        sponsored_product_urls = {p['url'] for p in sponsored_products if p.get('url')}
        
        basket_campaign_prices = self._extract_basket_campaign_prices(soup)
        
        urls = self._extract_product_urls_from_soup(soup, max_products, sponsored_urls=sponsored_product_urls)
        
        return {
            'urls': urls,
            'sponsored_brands': sponsored_brands,
            'sponsored_products': sponsored_products,
            'sponsored_product_urls': sponsored_product_urls,
            'basket_campaign_prices': basket_campaign_prices
        }
    
    async def _scrape_product_via_http_api(self, url: str, session_number: int = None) -> Optional[Dict[str, Any]]:
        """Scrape product detail page using ScraperAPI PROXY PORT method
        
        Strategy:
        1. First try ScraperAPI with JS render (for dynamic content like "sepete özel")
        2. If render fails (500 = premium required), fallback to standard ScraperAPI
        3. Parse product data and check for discounted_price
        """
        if session_number is None:
            session_number = random.randint(1, 10000)
        
        html = await self._fetch_with_scraperapi_proxy(
            url, 
            session_number=session_number,
            render_js=True,
            wait_for_selector='[data-test-id="price-current-price"]'
        )
        
        if not html:
            logger.debug("JS render failed, trying standard ScraperAPI...")
            html = await self._fetch_with_scraperapi_proxy(url, session_number=session_number)
        product_data = None
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            utag_data = self._extract_utag_data(html)
            json_ld_data = self._extract_json_ld_data(soup)
            
            product_data = {
                "platform": "hepsiburada",
                "url": url,
                "external_id": self._extract_external_id(url),
            }
            
            if utag_data:
                product_data.update(self._parse_utag_data(utag_data))
            
            if json_ld_data:
                if not product_data.get("name"):
                    product_data["name"] = json_ld_data.get("name")
                if not product_data.get("brand"):
                    product_data["brand"] = json_ld_data.get("brand", {}).get("name") if isinstance(json_ld_data.get("brand"), dict) else json_ld_data.get("brand")
                if not product_data.get("rating") and json_ld_data.get("aggregateRating"):
                    product_data["rating"] = self._parse_float(json_ld_data["aggregateRating"].get("ratingValue"))
                    product_data["reviews_count"] = self._parse_int(json_ld_data["aggregateRating"].get("reviewCount"))
                product_data["image_url"] = json_ld_data.get("image")
                product_data["description"] = json_ld_data.get("description")
            
            html_data = self._extract_html_data(soup)
            if html_data:
                if html_data.get("discounted_price"):
                    product_data["discounted_price"] = html_data["discounted_price"]
                    if product_data.get("price") and html_data["discounted_price"]:
                        product_data["discount_percentage"] = round((1 - html_data["discounted_price"] / product_data["price"]) * 100, 1)
                if html_data.get("coupons"):
                    product_data["coupons"] = html_data["coupons"]
                if html_data.get("campaigns"):
                    product_data["campaigns"] = html_data["campaigns"]
                if html_data.get("stock_count"):
                    product_data["stock_count"] = html_data["stock_count"]
                if html_data.get("origin_country"):
                    product_data["origin_country"] = html_data["origin_country"]
                if html_data.get("description"):
                    product_data["description"] = html_data["description"]
                if html_data.get("image_url") and not product_data.get("image_url"):
                    product_data["image_url"] = html_data["image_url"]
            
            if not product_data.get("name"):
                title = soup.find("h1")
                if title:
                    product_data["name"] = title.get_text(strip=True)
            
            product_data['other_sellers'] = self._extract_other_sellers(soup)
            product_data['reviews'] = self._extract_reviews(soup)
            
            if settings.DEBUG_SAVE_HTML:
                debug_dir = "/tmp/scraping_debug"
                os.makedirs(debug_dir, exist_ok=True)
                external_id = product_data.get('external_id', 'unknown')
                debug_file = f"{debug_dir}/product_{external_id}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.debug(f"Saved product HTML to {debug_file}")
                logger.debug(f"Extracted {len(product_data.get('other_sellers', []))} sellers, {len(product_data.get('reviews', []))} reviews, discount: {product_data.get('discounted_price', 'N/A')}")
            
            return product_data
        
        logger.warning(f"ScraperAPI failed for product: {url[:60]}...")
        return None
    
    async def scrape_hepsiburada_search(self, keyword: str, max_products: int = MAX_PRODUCTS_PER_SEARCH) -> Dict[str, Any]:
        """Scrape Hepsiburada search results
        
        Returns dict with:
        - products: List of scraped ORGANIC product data (excludes sponsored)
        - sponsored_brands: List of brand carousel ads (AUTO POWER, MTS Kimya vb.)
        - sponsored_products: List of sponsored products with display order
        """
        provider = proxy_manager.get_primary_provider()
        self.current_provider_name = provider.name if provider else "direct"
        
        sponsored_brands = []
        sponsored_products = []
        sponsored_product_urls = set()
        basket_campaign_prices = {}
        
        if self.current_provider_name == "scraperapi":
            search_result = await self._get_product_urls_via_http_api(keyword, max_products)
            product_urls = search_result['urls']
            sponsored_brands = search_result['sponsored_brands']
            sponsored_products = search_result.get('sponsored_products', [])
            sponsored_product_urls = search_result['sponsored_product_urls']
            basket_campaign_prices = search_result.get('basket_campaign_prices', {})
        else:
            if not self.browser:
                await self.init_browser()
            product_urls = await self._get_product_urls_from_search(keyword, max_products)
        
        logger.info(f"Found {len(product_urls)} product URLs to scrape (using {self.current_provider_name})")
        if basket_campaign_prices:
            logger.info(f"Found {len(basket_campaign_prices)} basket campaign prices from search page")
        
        products = []
        for i, url in enumerate(product_urls[:max_products]):
            logger.info(f"Scraping product {i+1}/{len(product_urls[:max_products])}: {url[:60]}...")
            try:
                product_data = await self.scrape_product_detail_page(url)
                if product_data:
                    if url in sponsored_product_urls:
                        product_data['is_sponsored'] = True
                    
                    if url in basket_campaign_prices and not product_data.get('discounted_price'):
                        product_data['discounted_price'] = basket_campaign_prices[url]
                        if product_data.get('price') and basket_campaign_prices[url]:
                            product_data['discount_percentage'] = round((1 - basket_campaign_prices[url] / product_data['price']) * 100, 1)
                        logger.debug(f"Applied basket campaign price from search: {basket_campaign_prices[url]} TL")
                    
                    products.append(product_data)
                    logger.debug(f"Scraped: {product_data.get('name', 'Unknown')[:50]}")
                await self._random_delay(1000, 3000)
            except Exception as e:
                debug_logger.log_error(url, self.current_provider_name, e)
                continue
        
        logger.info(f"Scraped {len(products)} organic products, {len(sponsored_products)} sponsored, {len(sponsored_brands)} brand ads")
        return {
            'products': products,
            'sponsored_brands': sponsored_brands,
            'sponsored_products': sponsored_products
        }
    
    async def _get_product_urls_from_search(self, keyword: str, max_products: int, retry_count: int = 0) -> List[str]:
        page = await self.context.new_page()
        await stealth.apply_stealth_async(page)
        await self._apply_anti_detection(page)
        
        urls = []
        search_url = f"https://www.hepsiburada.com/ara?q={keyword.replace(' ', '+')}"
        
        try:
            logger.info(f"Fetching search results: {search_url[:60]}...")
            logger.debug(f"Using provider: {self.current_provider_name}")
            
            response = await page.goto(search_url, timeout=90000, wait_until="domcontentloaded")
            status = response.status if response else 0
            logger.debug(f"Search page response: {status}")
            
            debug_logger.log_request(search_url, self.current_provider_name, status)
            
            if status in [403, 429, 503]:
                content = await page.content()
                debug_logger.save_debug_html(search_url, content, status, self.current_provider_name)
                logger.error(f"Received {status} status - possible bot detection or rate limiting")
                await page.close()
                
                if retry_count < MAX_RETRIES and self.current_provider_name != "direct":
                    logger.info(f"Attempting fallback (retry {retry_count + 1}/{MAX_RETRIES})...")
                    if await self.reinit_with_fallback():
                        return await self._get_product_urls_from_search(keyword, max_products, retry_count + 1)
                return []
            
            await self._random_delay(3000, 5000)
            await self._simulate_human_behavior(page)
            
            content = await page.content()
            
            if "captcha" in content.lower() or "robot" in content.lower():
                debug_logger.save_debug_html(search_url, content, status, self.current_provider_name)
                logger.warning("CAPTCHA or robot detection detected!")
                return []
            
            soup = BeautifulSoup(content, 'html.parser')
            urls = self._extract_product_urls_from_soup(soup, max_products)
            
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
    
    async def _scrape_product_via_playwright(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape product using Playwright with Bright Data proxy for JS-rendered content
        
        This is used as a fallback when ScraperAPI doesn't find discounted_price.
        It only returns html_data (discounted_price, coupons, campaigns, etc.)
        to be merged with the ScraperAPI product_data.
        """
        if not self.browser or not self.context:
            await self.init_browser("brightdata")
        
        page = await self.context.new_page()
        await stealth.apply_stealth_async(page)
        await self._apply_anti_detection(page)
        
        try:
            logger.debug(f"Playwright scraping: {url[:60]}...")
            response = await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            status = response.status if response else 0
            
            if status not in [200, 301, 302]:
                logger.warning(f"Playwright bad response for {url[:50]}: {status}")
                return None
            
            try:
                await page.wait_for_selector('[data-test-id="price-current-price"], [class*="price"], .product-price', timeout=10000)
            except:
                pass
            
            await self._random_delay(2000, 3000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            html_data = self._extract_html_data(soup)
            
            if settings.DEBUG_SAVE_HTML:
                debug_dir = "/tmp/scraping_debug"
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = f"{debug_dir}/playwright_{self._extract_external_id(url)}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.debug(f"Saved Playwright HTML to {debug_file}")
            
            return html_data
            
        except Exception as e:
            logger.error(f"Playwright error for {url[:50]}: {e}")
            return None
        finally:
            await page.close()
    
    async def scrape_product_detail_page(self, url: str) -> Optional[Dict[str, Any]]:
        if self.current_provider_name == "scraperapi":
            product_data = await self._scrape_product_via_http_api(url)
            
            if not product_data:
                logger.info(f"ScraperAPI failed, falling back to Playwright: {url[:50]}...")
                self.current_provider_name = "brightdata"
                if self.browser:
                    await self.close_browser()
                await self.init_browser("brightdata")
            else:
                return product_data
        
        if not self.context:
            if not self.browser:
                await self.init_browser()
        
        page = await self.context.new_page()
        await stealth.apply_stealth_async(page)
        await self._apply_anti_detection(page)
        
        try:
            response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            status = response.status if response else 0
            
            debug_logger.log_request(url, self.current_provider_name, status)
            
            if status not in [200, 301, 302]:
                logger.warning(f"Bad response for {url[:50]}: {status}")
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
            match = re.search(r'const\s+utagData\s*=\s*(\{.*?\});\s*\n?\s*window\.utagData', html_content, re.DOTALL)
            if not match:
                match = re.search(r'const\s+utagData\s*=\s*(\{[^}]+(?:\{[^}]*\}[^}]*)*\});', html_content)
            if not match:
                start = html_content.find('const utagData = {')
                if start != -1:
                    brace_count = 0
                    json_start = html_content.find('{', start)
                    for i, char in enumerate(html_content[json_start:], json_start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = html_content[json_start:i+1]
                                break
                    else:
                        return None
                else:
                    return None
            else:
                json_str = match.group(1)
            
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            result = json.loads(json_str)
            logger.debug(f"utagData extracted: {list(result.keys())[:10]}...")
            return result
        except Exception as e:
            logger.debug(f"Error extracting utagData: {e}")
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
            logger.debug(f"Error extracting JSON-LD: {e}")
        return None
    
    def _parse_float(self, value) -> Optional[float]:
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            value_str = str(value).strip()
            if ',' in value_str and '.' in value_str:
                if value_str.rfind(',') > value_str.rfind('.'):
                    value_str = value_str.replace('.', '')
                    value_str = value_str.replace(',', '.')
                else:
                    value_str = value_str.replace(',', '')
            elif ',' in value_str:
                value_str = value_str.replace(',', '.')
            value_str = re.sub(r'[^\d.]', '', value_str)
            return float(value_str) if value_str else None
        except:
            return None
    
    def _parse_int(self, value) -> Optional[int]:
        if value is None:
            return None
        try:
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            value_str = str(value).strip()
            value_str = re.sub(r'[^\d]', '', value_str)
            return int(value_str) if value_str else None
        except:
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
                price_str = str(utag['product_prices'][0])
                if ',' in price_str and '.' in price_str:
                    if price_str.rfind(',') < price_str.rfind('.'):
                        price_str = price_str.replace(',', '')
                    else:
                        price_str = price_str.replace('.', '').replace(',', '.')
                elif ',' in price_str:
                    price_str = price_str.replace(',', '.')
                data['price'] = float(price_str)
                logger.debug(f"Parsed price: {data['price']} from {utag['product_prices'][0]}")
            except Exception as e:
                logger.debug(f"Error parsing price: {e}")
        
        logger.debug(f"utag result: name={data.get('name', 'N/A')[:30] if data.get('name') else 'N/A'}, price={data.get('price')}")
        
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
        
        discounted_price = None
        
        sepete_ozel_selectors = [
            '[class*="isBasketCampaign"]',
            '[class*="priceAreaRoot"][class*="isBasketCampaign"]',
            '[class*="sepete"]',
            '[class*="Sepete"]',
            '[class*="cartSpecial"]',
            '[class*="campaignPrice"]',
            '[class*="specialPrice"]',
            '[data-test-id*="campaign"]',
            '[class*="discountedPrice"]',
            '[class*="DiscountedPrice"]',
        ]
        
        for selector in sepete_ozel_selectors:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.get_text(strip=True)
                price_match = re.search(r'([\d.]+,\d+)', price_text)
                if price_match:
                    try:
                        price_str = price_match.group(1).replace('.', '').replace(',', '.')
                        discounted_price = float(price_str)
                        logger.debug(f"Found sepete özel price via {selector}: {discounted_price}")
                        break
                    except:
                        pass
        
        if not discounted_price:
            sepete_patterns = [
                r'Sepete\s+özel[^0-9]*([\d.]+,\d+)',
                r'Sepette[^0-9]*([\d.]+,\d+)',
                r'sepete\s+özel[^0-9]*([\d.]+,\d+)',
                r'Size\s+özel[^0-9]*([\d.]+,\d+)',
                r'Sepete\s+özel[^0-9]*([\d.]+,\d+)\s*[₺TL]',
                r'([\d.]+,\d+)\s*₺.*?[Ss]epete',
            ]
            html_text = str(soup)
            for pattern in sepete_patterns:
                match = re.search(pattern, html_text, re.IGNORECASE)
                if match:
                    try:
                        price_str = match.group(1).replace('.', '').replace(',', '.')
                        discounted_price = float(price_str)
                        logger.debug(f"Found sepete özel price: {discounted_price}")
                        break
                    except:
                        pass
        
        if not discounted_price:
            campaign_price = soup.find(string=re.compile(r'Sepete özel fiyat|sepete ekleyin|Size özel', re.IGNORECASE))
            if campaign_price:
                parent = campaign_price.find_parent()
                if parent:
                    for _ in range(5):
                        parent_text = parent.get_text()
                        price_match = re.search(r'([\d.]+,\d+)\s*[₺TL]', parent_text)
                        if price_match:
                            try:
                                price_str = price_match.group(1).replace('.', '').replace(',', '.')
                                discounted_price = float(price_str)
                                logger.debug(f"Found sepete özel price via parent: {discounted_price}")
                                break
                            except:
                                pass
                        parent = parent.find_parent()
                        if not parent:
                            break
        
        if discounted_price:
            data['discounted_price'] = discounted_price
        
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
        
        desc_elem = soup.select_one('.productDescriptionContent')
        if not desc_elem:
            desc_elem = soup.select_one('[class*="ProductDescription"]')
        if not desc_elem:
            desc_elem = soup.select_one('[data-test-id="product-description"]')
        if desc_elem:
            desc_text = desc_elem.get_text(strip=True)
            if desc_text and 'Hepsiburada' not in desc_text[:100]:
                data['description'] = desc_text[:5000]
        
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
        html = str(soup)
        
        try:
            listings_start = html.find('"listings":[{"merchantId"')
            if listings_start != -1:
                start = html.find('[', listings_start)
                depth = 0
                end = start
                for i, c in enumerate(html[start:start+15000]):
                    if c == '[': depth += 1
                    elif c == ']': depth -= 1
                    if depth == 0 and c == ']':
                        end = start + i + 1
                        break
                
                listings_json = html[start:end]
                listings = json.loads(listings_json)
                
                merchant_data = {}
                mi_pattern = r'"merchantInfo":\{"id":"([^"]+)".*?(?="merchantInfo":|$)'
                for match in re.finditer(mi_pattern, html, re.DOTALL):
                    block = match.group(0)
                    merchant_id = match.group(1)
                    
                    name_match = re.search(r'"name":"([^"]+)"', block)
                    rating_match = re.search(r'"lifetimeRating":([0-9.]+)', block)
                    price_match = re.search(r'"prices":\[\{"formattedPrice":"[^"]+","value":([0-9.]+)', block)
                    
                    if name_match:
                        merchant_data[merchant_id] = {
                            'name': name_match.group(1),
                            'rating': float(rating_match.group(1)) if rating_match else None,
                            'price': float(price_match.group(1)) if price_match else None
                        }
                
                for listing in listings[:10]:
                    merchant_id = listing.get('merchantId')
                    merchant_name = listing.get('merchantName')
                    
                    if not merchant_name:
                        continue
                    
                    seller_data = {
                        'seller_name': merchant_name,
                        'merchant_id': merchant_id,
                        'is_authorized': False
                    }
                    
                    if merchant_id in merchant_data:
                        if merchant_data[merchant_id]['rating']:
                            seller_data['seller_rating'] = merchant_data[merchant_id]['rating']
                        if merchant_data[merchant_id]['price']:
                            seller_data['price'] = merchant_data[merchant_id]['price']
                    
                    sellers.append(seller_data)
                
                if sellers:
                    logger.debug(f"Extracted {len(sellers)} other sellers from JSON")
                    return sellers
        except Exception as e:
            logger.debug(f"Error extracting sellers from JSON: {e}")
        
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
        
        json_ld_scripts = soup.select('script[type="application/ld+json"]')
        for script in json_ld_scripts:
            try:
                script_content = script.string
                if not script_content:
                    continue
                data = json.loads(script_content)
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Review':
                            rating_obj = item.get('reviewRating', {})
                            rating_val = rating_obj.get('ratingValue') if isinstance(rating_obj, dict) else None
                            review = {
                                'author': item.get('author', 'Anonim'),
                                'rating': self._parse_float(rating_val),
                                'review_text': item.get('reviewBody', ''),
                                'review_date': item.get('datePublished')
                            }
                            reviews.append(review)
            except Exception as e:
                logger.debug(f"Error parsing JSON-LD for reviews: {e}")
                continue
        
        if not reviews:
            review_cards = soup.select('[class*="reviewCard"], [class*="ReviewCard"]')
            for card in review_cards[:20]:
                try:
                    author = card.select_one('[class*="author"], [class*="userName"]')
                    rating_elem = card.select_one('[class*="rating"], [class*="stars"]')
                    text_elem = card.select_one('[class*="text"], [class*="comment"], [class*="body"]')
                    date_elem = card.select_one('[class*="date"]')
                    
                    review = {
                        'author': author.get_text(strip=True) if author else 'Anonim',
                        'review_text': text_elem.get_text(strip=True) if text_elem else '',
                    }
                    
                    if rating_elem:
                        rating_text = rating_elem.get_text(strip=True)
                        rating_match = re.search(r'(\d+(?:[.,]\d+)?)', rating_text)
                        if rating_match:
                            review['rating'] = self._parse_float(rating_match.group(1))
                    
                    if date_elem:
                        review['review_date'] = date_elem.get_text(strip=True)
                    
                    if review.get('review_text'):
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
