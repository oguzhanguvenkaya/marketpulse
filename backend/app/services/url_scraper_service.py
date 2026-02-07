import os
import re
import json
import asyncio
import time
import aiohttp
import logging
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_stop_signals: dict[str, bool] = {}


def request_stop(job_id: str):
    _stop_signals[job_id] = True
    logger.info(f"[JOB {job_id[:8]}] Stop signal received")


def is_stop_requested(job_id: str) -> bool:
    return _stop_signals.get(job_id, False)


def clear_stop_signal(job_id: str):
    _stop_signals.pop(job_id, None)


class UrlScraperService:
    SCRAPERAPI_BASE_URL = "https://api.scraperapi.com"
    MAX_CONCURRENT = 15

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

        start = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url) as resp:
                    elapsed = round(time.time() - start, 1)
                    if resp.status == 200:
                        html = await resp.text()
                        logger.info(f"  FETCH OK  {url[:80]} — {elapsed}s, {len(html)} bytes")
                        return html
                    else:
                        body = await resp.text()
                        logger.warning(f"  FETCH FAIL {url[:80]} — HTTP {resp.status} in {elapsed}s — {body[:200]}")
                        return None
        except asyncio.TimeoutError:
            elapsed = round(time.time() - start, 1)
            logger.error(f"  FETCH TIMEOUT {url[:80]} — {elapsed}s")
            return None
        except Exception as e:
            elapsed = round(time.time() - start, 1)
            logger.error(f"  FETCH ERROR {url[:80]} — {elapsed}s — {type(e).__name__}: {e}")
            return None

    def _get_text_content(self, element) -> str:
        if element is None:
            return None
        if isinstance(element, str):
            return element.strip() or None
        for tag in element.find_all(['script', 'style', 'noscript']):
            tag.decompose()
        text = element.decode_contents()
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'</(p|div|li|tr|h[1-6])>', '\n', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip() or None

    def _extract_microdata(self, soup) -> dict:
        microdata = {}
        itemprop_map = {
            'name': 'product_name',
            'description': 'product_description',
            'brand': 'product_brand',
            'sku': 'product_sku',
            'gtin13': 'product_barcode',
            'gtin': 'product_barcode',
            'mpn': 'product_mpn',
            'color': 'product_color',
            'weight': 'product_weight',
            'category': 'product_category',
            'price': 'price',
            'priceCurrency': 'currency',
            'availability': 'availability',
            'ratingValue': 'rating',
            'reviewCount': 'review_count',
        }

        for prop_name, data_key in itemprop_map.items():
            elements = soup.find_all(attrs={'itemprop': prop_name})
            for el in elements:
                if el.name == 'meta':
                    val = el.get('content', '').strip()
                elif el.name == 'link':
                    val = el.get('href', '').strip()
                elif el.name in ('span', 'div', 'p', 'td', 'h1', 'h2', 'h3', 'h4', 'a', 'strong', 'b', 'em', 'time', 'data'):
                    if data_key == 'product_description':
                        val = self._get_text_content(el)
                    else:
                        val = el.get('content') or el.get_text(strip=True)
                else:
                    if data_key == 'product_description':
                        val = self._get_text_content(el)
                    else:
                        val = el.get('content') or el.get_text(strip=True)

                if val and data_key not in microdata:
                    microdata[data_key] = val

        return microdata

    def _extract_html_description(self, soup) -> str:
        desc_selectors = [
            {'id': re.compile(r'product.?desc|description|urun.?aciklama', re.I)},
            {'class_': re.compile(r'product.?desc|description|detail.?desc|urun.?aciklama|product.?detail.?content|product.?info', re.I)},
        ]
        for selector in desc_selectors:
            el = soup.find(['div', 'section', 'article', 'td'], attrs=selector)
            if el:
                text = self._get_text_content(el)
                if text and len(text) > 30:
                    return text

        tab_contents = soup.find_all(['div', 'section'], attrs={
            'class': re.compile(r'tab.?content|tab.?pane|tab.?panel', re.I)
        })
        for tab in tab_contents:
            text = self._get_text_content(tab)
            if text and len(text) > 50:
                return text

        return None

    def _extract_price_from_html(self, soup) -> dict:
        price_data = {}
        price_selectors = [
            {'class_': re.compile(r'product.?price|current.?price|sale.?price|fiyat|price.?now', re.I)},
            {'id': re.compile(r'product.?price|price|fiyat', re.I)},
        ]
        for selector in price_selectors:
            el = soup.find(['span', 'div', 'p', 'ins', 'strong', 'b', 'data'], attrs=selector)
            if el:
                price_text = el.get('content') or el.get_text(strip=True)
                price_match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.') if ',' in price_text else price_text)
                if price_match:
                    price_data['price'] = price_match.group(0)
                    break

        old_price_selectors = [
            {'class_': re.compile(r'old.?price|original.?price|list.?price|was.?price|eski.?fiyat|price.?was', re.I)},
        ]
        for selector in old_price_selectors:
            el = soup.find(['span', 'div', 'p', 'del', 's', 'strike', 'data'], attrs=selector)
            if el:
                price_text = el.get('content') or el.get_text(strip=True)
                price_match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.') if ',' in price_text else price_text)
                if price_match:
                    price_data['original_price'] = price_match.group(0)
                    break

        return price_data

    def _extract_product_specs(self, soup) -> dict:
        specs = {}
        spec_tables = soup.find_all('table', attrs={
            'class': re.compile(r'spec|feature|attribute|property|ozellik|detail', re.I)
        })
        if not spec_tables:
            spec_tables = soup.find_all('table')

        for table in spec_tables[:3]:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    if key and val and len(key) < 100:
                        specs[key] = val

        dl_elements = soup.find_all('dl')
        for dl in dl_elements[:3]:
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                key = dt.get_text(strip=True)
                val = dd.get_text(strip=True)
                if key and val:
                    specs[key] = val

        return specs if specs else None

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
                raw = script.string or script.get_text()
                if not raw or not raw.strip():
                    continue
                ld = json.loads(raw)
                json_ld_data.append(ld)
                items = []
                if isinstance(ld, dict):
                    if '@graph' in ld:
                        items = ld['@graph'] if isinstance(ld['@graph'], list) else [ld['@graph']]
                    else:
                        items = [ld]
                elif isinstance(ld, list):
                    items = ld
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    ld_type = item.get('@type', '')
                    is_product = ld_type == 'Product' or (isinstance(ld_type, list) and 'Product' in ld_type)
                    if is_product:
                        if not data.get('product_name'):
                            data['product_name'] = item.get('name')
                        if not data.get('product_description'):
                            data['product_description'] = item.get('description')
                        brand = item.get('brand')
                        if not data.get('product_brand'):
                            data['product_brand'] = brand.get('name') if isinstance(brand, dict) else brand
                        if not data.get('product_sku'):
                            data['product_sku'] = item.get('sku')
                        if not data.get('product_barcode'):
                            data['product_barcode'] = item.get('gtin13') or item.get('gtin') or item.get('gtin12') or item.get('gtin14')
                        if not data.get('product_mpn'):
                            data['product_mpn'] = item.get('mpn')
                        if not data.get('product_image'):
                            data['product_image'] = item.get('image')
                        if not data.get('product_color'):
                            data['product_color'] = item.get('color')
                        if not data.get('product_weight'):
                            weight = item.get('weight')
                            data['product_weight'] = weight.get('value') if isinstance(weight, dict) else weight
                        if not data.get('product_category'):
                            data['product_category'] = item.get('category')

                        offers = item.get('offers', {})
                        offer_list = [offers] if isinstance(offers, dict) else offers if isinstance(offers, list) else []
                        if offer_list:
                            offer = offer_list[0] if isinstance(offer_list[0], dict) else {}
                            if not data.get('price'):
                                data['price'] = offer.get('price')
                            data['currency'] = offer.get('priceCurrency', data.get('currency'))
                            data['availability'] = offer.get('availability')
                            if offer.get('seller'):
                                seller = offer['seller']
                                data['seller_name'] = seller.get('name') if isinstance(seller, dict) else seller

                        agg = item.get('aggregateRating')
                        if agg and isinstance(agg, dict):
                            data['rating'] = agg.get('ratingValue')
                            data['review_count'] = agg.get('reviewCount')
            except (json.JSONDecodeError, TypeError):
                continue
        if json_ld_data:
            data['json_ld'] = json_ld_data

        microdata = self._extract_microdata(soup)
        for key, val in microdata.items():
            if not data.get(key):
                data[key] = val

        if not data.get('product_description'):
            data['product_description'] = self._extract_html_description(soup)

        if not data.get('price'):
            html_prices = self._extract_price_from_html(soup)
            data.update({k: v for k, v in html_prices.items() if not data.get(k)})

        specs = self._extract_product_specs(soup)
        if specs:
            data['product_specs'] = specs

        images = []
        for img in soup.find_all('img', attrs={'itemprop': 'image'}):
            src = img.get('src') or img.get('data-src')
            if src:
                images.append(src)
        if og_data.get('image') and og_data['image'] not in images:
            images.append(og_data['image'])
        product_img_containers = soup.find_all(['div', 'ul'], attrs={
            'class': re.compile(r'product.?image|gallery|slider|carousel|urun.?resim', re.I)
        })
        for container in product_img_containers[:2]:
            for img in container.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('data-zoom-image') or img.get('data-large')
                if src and src not in images:
                    images.append(src)
        if not images:
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src and not any(x in src.lower() for x in ['icon', 'logo', 'sprite', 'pixel', 'tracking', '.svg', 'data:', 'placeholder']):
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

    async def scrape_urls_batch(self, result_ids_urls: list[tuple], db_factory, job_id: str = None):
        total = len(result_ids_urls)
        completed_count = 0
        failed_count = 0
        batch_start = time.time()
        stopped = False
        jid = (job_id or '?')[:8]

        logger.info(f"[JOB {jid}] Starting batch: {total} URLs, concurrency={self.MAX_CONCURRENT}")

        queue: asyncio.Queue = asyncio.Queue()
        for item in result_ids_urls:
            await queue.put(item)

        write_lock = asyncio.Lock()

        async def worker():
            nonlocal completed_count, failed_count, stopped
            while True:
                if job_id and is_stop_requested(job_id):
                    stopped = True
                    return

                try:
                    result_id, url = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return

                url_start = time.time()
                status = 'failed'
                scraped_data = None
                error_message = None

                try:
                    scraped = await self.scrape_url(url)
                    if 'error' not in scraped:
                        status = 'completed'
                        scraped_data = scraped
                        completed_count += 1
                    else:
                        error_message = scraped.get('error')
                        scraped_data = scraped
                        failed_count += 1
                except Exception as e:
                    error_message = str(e)
                    failed_count += 1
                    logger.error(f"[JOB {jid}] Exception scraping {url[:60]}: {e}")

                url_elapsed = round(time.time() - url_start, 1)
                done = completed_count + failed_count
                logger.info(
                    f"[JOB {jid}] [{done}/{total}] "
                    f"{'OK' if status == 'completed' else 'FAIL'} "
                    f"{url[:70]} — {url_elapsed}s"
                )

                async with write_lock:
                    db = db_factory()
                    try:
                        from app.db.models import ScrapeResult
                        db.query(ScrapeResult).filter(ScrapeResult.id == result_id).update({
                            'status': status,
                            'scraped_data': scraped_data,
                            'error_message': error_message,
                        })
                        db.commit()
                    except Exception as e:
                        logger.error(f"[JOB {jid}] DB write error for result {result_id}: {e}")
                        db.rollback()
                    finally:
                        db.close()

        workers = [asyncio.create_task(worker()) for _ in range(self.MAX_CONCURRENT)]
        await asyncio.gather(*workers, return_exceptions=True)

        if job_id and is_stop_requested(job_id):
            stopped = True

        skipped_count = 0
        if stopped:
            db = db_factory()
            try:
                from app.db.models import ScrapeResult
                import uuid as uuid_mod
                skipped_count = db.query(ScrapeResult).filter(
                    ScrapeResult.scrape_job_id == uuid_mod.UUID(job_id),
                    ScrapeResult.status == 'pending'
                ).update({'status': 'skipped'})
                db.commit()
                logger.info(f"[JOB {jid}] Marked {skipped_count} remaining URLs as skipped")
            except Exception as e:
                logger.error(f"[JOB {jid}] Error marking skipped: {e}")
                db.rollback()
            finally:
                db.close()

        batch_elapsed = round(time.time() - batch_start, 1)
        logger.info(
            f"[JOB {jid}] Batch finished in {batch_elapsed}s — "
            f"OK: {completed_count}, FAIL: {failed_count}, SKIPPED: {skipped_count}, TOTAL: {total}"
            + (" (STOPPED by user)" if stopped else "")
        )

        if job_id:
            clear_stop_signal(job_id)

        return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count, "stopped": stopped}
