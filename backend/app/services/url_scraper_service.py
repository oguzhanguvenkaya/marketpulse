import os
import json
import asyncio
import aiohttp
import logging
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class UrlScraperService:
    SCRAPERAPI_BASE_URL = "https://api.scraperapi.com"
    MAX_CONCURRENT = 5

    def __init__(self):
        self.api_key = os.environ.get('SCRAPPER_API', '')
        if not self.api_key:
            try:
                with open('/etc/secrets/SCRAPPER_API', 'r') as f:
                    self.api_key = f.read().strip()
            except:
                pass
        self._semaphore = None

    async def fetch_url(self, url: str) -> str | None:
        if not self.api_key:
            logger.error("ScraperAPI key not found")
            return None

        encoded_url = quote_plus(url)
        api_url = f"{self.SCRAPERAPI_BASE_URL}?api_key={self.api_key}&url={encoded_url}&render=false"

        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        logger.error(f"ScraperAPI error {resp.status} for {url[:60]}")
                        return None
        except Exception as e:
            logger.error(f"Fetch error for {url[:60]}: {e}")
            return None

    def parse_html(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        data = {'source_url': url}

        title_tag = soup.find('title')
        data['page_title'] = title_tag.get_text(strip=True) if title_tag else None

        h1 = soup.find('h1')
        data['h1'] = h1.get_text(strip=True) if h1 else None

        meta_desc = soup.find('meta', attrs={'name': 'description'})
        data['meta_description'] = meta_desc.get('content', '') if meta_desc else None

        og_data = {}
        for og_tag in soup.find_all('meta', attrs={'property': lambda v: v and v.startswith('og:')}):
            key = og_tag.get('property', '').replace('og:', '')
            og_data[key] = og_tag.get('content', '')
        if og_data:
            data['og_data'] = og_data
            if not data['page_title'] and og_data.get('title'):
                data['page_title'] = og_data['title']

        price_tag = soup.find('meta', attrs={'property': 'og:price:amount'}) or soup.find('meta', attrs={'property': 'product:price:amount'})
        if price_tag:
            data['price'] = price_tag.get('content')
        currency_tag = soup.find('meta', attrs={'property': 'og:price:currency'}) or soup.find('meta', attrs={'property': 'product:price:currency'})
        if currency_tag:
            data['currency'] = currency_tag.get('content')

        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        json_ld_data = []
        for script in json_ld_scripts:
            try:
                ld = json.loads(script.string)
                json_ld_data.append(ld)
                if isinstance(ld, dict):
                    ld_type = ld.get('@type', '')
                    if ld_type == 'Product' or (isinstance(ld_type, list) and 'Product' in ld_type):
                        data['product_name'] = ld.get('name')
                        data['product_description'] = ld.get('description')
                        data['product_brand'] = ld.get('brand', {}).get('name') if isinstance(ld.get('brand'), dict) else ld.get('brand')
                        data['product_sku'] = ld.get('sku')
                        data['product_image'] = ld.get('image')
                        offers = ld.get('offers', {})
                        if isinstance(offers, dict):
                            if not data.get('price'):
                                data['price'] = offers.get('price')
                            data['currency'] = offers.get('priceCurrency', data.get('currency'))
                            data['availability'] = offers.get('availability')
                        elif isinstance(offers, list) and offers:
                            if not data.get('price'):
                                data['price'] = offers[0].get('price')
                            data['currency'] = offers[0].get('priceCurrency', data.get('currency'))
                        if ld.get('aggregateRating'):
                            data['rating'] = ld['aggregateRating'].get('ratingValue')
                            data['review_count'] = ld['aggregateRating'].get('reviewCount')
            except (json.JSONDecodeError, TypeError):
                continue
        if json_ld_data:
            data['json_ld'] = json_ld_data

        images = []
        for img in soup.find_all('img', attrs={'itemprop': 'image'}):
            src = img.get('src') or img.get('data-src')
            if src:
                images.append(src)
        if og_data.get('image') and og_data['image'] not in images:
            images.append(og_data['image'])
        if not images:
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src and not any(x in src.lower() for x in ['icon', 'logo', 'sprite', 'pixel', 'tracking', '.svg', 'data:']):
                    images.append(src)
                    if len(images) >= 5:
                        break
        data['images'] = images[:10]

        return data

    async def scrape_url(self, url: str) -> dict:
        html = await self.fetch_url(url)
        if not html:
            return {'source_url': url, 'error': 'Failed to fetch URL'}
        return self.parse_html(html, url)

    async def scrape_urls_batch(self, results, db):
        if not self._semaphore:
            self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)

        async def process_one(result):
            async with self._semaphore:
                try:
                    scraped = await self.scrape_url(result.url)
                    result.scraped_data = scraped
                    result.status = 'completed' if 'error' not in scraped else 'failed'
                    result.error_message = scraped.get('error')
                except Exception as e:
                    result.status = 'failed'
                    result.error_message = str(e)
                db.add(result)
                db.commit()
                return result

        tasks = [process_one(r) for r in results]
        await asyncio.gather(*tasks)
