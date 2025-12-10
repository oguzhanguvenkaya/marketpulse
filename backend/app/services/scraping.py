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

stealth = Stealth()

class ScrapingService:
    def __init__(self):
        self.proxy_config = settings.bright_data_proxy_config
        self.browser: Optional[Browser] = None
        self.playwright = None
    
    async def init_browser(self):
        self.playwright = await async_playwright().start()
        
        if self.proxy_config:
            print(f"Launching browser with Bright Data Residential Proxy...")
            print(f"Proxy server: {self.proxy_config['server']}")
            print(f"Username: {self.proxy_config['username']}")
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                proxy=self.proxy_config
            )
            print("Browser launched with Bright Data proxy!")
        else:
            print("No Bright Data credentials, using local browser")
            self.browser = await self.playwright.chromium.launch(headless=True)
        
        return self.browser
    
    async def close_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def scrape_hepsiburada_search(self, keyword: str, max_products: int = 100) -> List[Dict[str, Any]]:
        if not self.browser:
            await self.init_browser()
        
        products = []
        context = await self.browser.new_context(
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
        page = await context.new_page()
        
        await stealth.apply_stealth_async(page)
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        try:
            search_url = f"https://www.hepsiburada.com/ara?q={keyword.replace(' ', '+')}"
            print(f"Scraping URL: {search_url}")
            
            response = await page.goto(search_url, timeout=90000, wait_until="domcontentloaded")
            print(f"Response status: {response.status if response else 'No response'}")
            print(f"Response URL: {response.url if response else 'No URL'}")
            
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            await page.mouse.move(random.randint(100, 500), random.randint(100, 300))
            await page.wait_for_timeout(random.randint(500, 1000))
            
            current_url = page.url
            page_title = await page.title()
            print(f"Current URL: {current_url}")
            print(f"Page title: {page_title}")
            
            if "güvenlik" in page_title.lower() or "security" in page_title.lower():
                print("Security page detected, waiting longer...")
                await page.wait_for_timeout(10000)
            
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await page.wait_for_timeout(2000)
            except:
                pass
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            print(f"Page title: {soup.title.string if soup.title else 'No title'}")
            print(f"Content length: {len(content)}")
            
            product_cards = soup.select('li[class*="productListContent"]')
            print(f"Found {len(product_cards)} product cards with productListContent")
            
            if not product_cards:
                product_cards = soup.select('[data-test-id="product-card-item"]')
                print(f"Found {len(product_cards)} product cards with data-test-id")
            
            if not product_cards:
                product_cards = soup.select('div[class*="moria-ProductCard"]')
                print(f"Found {len(product_cards)} product cards with moria-ProductCard")
            
            if not product_cards:
                all_links = soup.select('a[href*="-p-"]')
                print(f"Found {len(all_links)} links with -p- pattern")
                seen_parents = set()
                for link in all_links:
                    parent = link.find_parent('li') or link.find_parent('div', class_=lambda x: x and 'product' in x.lower() if x else False)
                    if parent and id(parent) not in seen_parents:
                        seen_parents.add(id(parent))
                        product_cards.append(parent)
                print(f"Extracted {len(product_cards)} unique product containers")
            
            for i, card in enumerate(product_cards[:max_products]):
                try:
                    product = self._parse_hepsiburada_card(card, debug=(i < 3))
                    if product:
                        products.append(product)
                except Exception as e:
                    print(f"Parse error: {e}")
                    continue
            
            print(f"Successfully parsed {len(products)} products")
            
        except Exception as e:
            print(f"Scraping error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await page.close()
        
        return products
    
    def _parse_hepsiburada_card(self, card, debug=False) -> Optional[Dict[str, Any]]:
        try:
            link_elem = card.select_one('a[href*="-p-"]') or card.select_one('a[href*="/"]')
            url = ""
            external_id = ""
            if link_elem:
                href = link_elem.get('href', '')
                if href.startswith('/'):
                    url = f"https://www.hepsiburada.com{href}"
                elif href.startswith('http'):
                    url = href
                else:
                    url = f"https://www.hepsiburada.com/{href}"
                match = re.search(r'-p-(\w+)', url)
                if match:
                    external_id = match.group(1)
            
            if debug:
                print(f"DEBUG - URL: {url[:80] if url else 'None'}...")
            
            name_elem = card.select_one('[data-test-id="product-card-name"]') or \
                       card.select_one('h3') or \
                       card.select_one('[class*="productName"]') or \
                       card.select_one('[class*="product-title"]') or \
                       card.select_one('a[title]') or \
                       card.select_one('span[title]')
            name = ""
            if name_elem:
                name = name_elem.get('title') or name_elem.get_text(strip=True)
            
            if debug:
                print(f"DEBUG - Name: {name[:50] if name else 'None'}...")
            
            price_elem = card.select_one('[data-test-id="price-current-price"]') or \
                        card.select_one('[class*="price"]')
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.'))
                if price_match:
                    try:
                        price = float(price_match.group())
                    except:
                        pass
            
            rating_elem = card.select_one('[class*="rating"]') or card.select_one('[data-test-id="rating"]')
            rating = None
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'[\d.]+', rating_text)
                if rating_match:
                    try:
                        rating = float(rating_match.group())
                    except:
                        pass
            
            reviews_elem = card.select_one('[class*="review"]') or card.select_one('[data-test-id="review-count"]')
            reviews_count = 0
            if reviews_elem:
                reviews_text = reviews_elem.get_text(strip=True)
                reviews_match = re.search(r'[\d.]+', reviews_text.replace('.', ''))
                if reviews_match:
                    try:
                        reviews_count = int(reviews_match.group())
                    except:
                        pass
            
            img_elem = card.select_one('img')
            image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else None
            
            is_sponsored = bool(card.select_one('[class*="sponsored"]') or 
                              card.select_one('[data-test-id="sponsored"]') or
                              'sponsor' in str(card).lower())
            
            seller_elem = card.select_one('[class*="seller"]') or card.select_one('[data-test-id="seller"]')
            seller_name = seller_elem.get_text(strip=True) if seller_elem else None
            
            if debug:
                print(f"DEBUG - Final check: name={bool(name)}, url={bool(url)}")
            
            if not name and not url:
                return None
            
            if not url and external_id:
                url = f"https://www.hepsiburada.com/-p-{external_id}"
            
            return {
                "platform": "hepsiburada",
                "external_id": external_id or url.split('/')[-1],
                "name": name,
                "url": url,
                "price": price,
                "rating": rating,
                "reviews_count": reviews_count,
                "image_url": image_url,
                "is_sponsored": is_sponsored,
                "seller_name": seller_name,
                "in_stock": True
            }
        except Exception as e:
            return None
    
    async def scrape_product_details(self, url: str) -> Optional[Dict[str, Any]]:
        if not self.browser:
            await self.init_browser()
        
        page = await self.browser.new_page()
        
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            name_elem = soup.select_one('h1') or soup.select_one('[data-test-id="product-name"]')
            name = name_elem.get_text(strip=True) if name_elem else ""
            
            price_elem = soup.select_one('[data-test-id="price-current-price"]') or \
                        soup.select_one('[class*="price"]')
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.'))
                if price_match:
                    try:
                        price = float(price_match.group())
                    except:
                        pass
            
            return {
                "name": name,
                "price": price,
                "url": url
            }
        except Exception as e:
            print(f"Product detail error: {e}")
            return None
        finally:
            await page.close()
