import re
import json
import asyncio
import time
import aiohttp
import logging
from typing import Optional
from urllib.parse import quote_plus, urlparse, urlencode, parse_qs, urlunparse
from bs4 import BeautifulSoup
from app.core.config import settings

logger = logging.getLogger(__name__)

_stop_signals: dict[str, bool] = {}


def request_stop(session_id: str):
    _stop_signals[session_id] = True


def is_stop_requested(session_id: str) -> bool:
    return _stop_signals.get(session_id, False)


def clear_stop_signal(session_id: str):
    _stop_signals.pop(session_id, None)


class CategoryScraperService:
    SCRAPERAPI_BASE_URL = "https://api.scraperapi.com"
    MAX_CONCURRENT = 40

    def __init__(self):
        self.api_key = (settings.SCRAPER_API_KEY or "").strip()

    @staticmethod
    def _get_geo_country(url: str) -> str:
        _tr_domains = {'hepsiburada.com', 'trendyol.com', 'n11.com', 'amazon.com.tr'}
        try:
            domain = urlparse(url).netloc.lower().replace('www.', '')
            for td in _tr_domains:
                if domain.endswith(td):
                    return 'eu'
        except Exception:
            pass
        return 'us'

    def detect_platform(self, url: str) -> str:
        domain = urlparse(url).netloc.lower().replace('www.', '')
        if 'hepsiburada.com' in domain:
            return 'hepsiburada'
        elif 'trendyol.com' in domain:
            return 'trendyol'
        return 'other'

    async def fetch_page(self, url: str) -> Optional[str]:
        if not self.api_key:
            logger.error("ScraperAPI key not found")
            return None

        geo_country = self._get_geo_country(url)
        encoded_url = quote_plus(url)
        api_url = f"{self.SCRAPERAPI_BASE_URL}?api_key={self.api_key}&url={encoded_url}&render=false&country_code={geo_country}"

        start = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url) as resp:
                    elapsed = round(time.time() - start, 1)
                    if resp.status == 200:
                        html = await resp.text()
                        logger.info(f"  CATEGORY FETCH OK  {url[:80]} — {elapsed}s, {len(html)} bytes")
                        return html
                    else:
                        body = await resp.text()
                        logger.warning(f"  CATEGORY FETCH FAIL {url[:80]} — HTTP {resp.status} in {elapsed}s — {body[:200]}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"  CATEGORY FETCH TIMEOUT {url[:80]}")
            return None
        except Exception as e:
            logger.error(f"  CATEGORY FETCH ERROR {url[:80]} — {type(e).__name__}: {e}")
            return None

    def build_page_url(self, base_url: str, page: int) -> str:
        parsed = urlparse(base_url)
        qs = parse_qs(parsed.query)
        platform = self.detect_platform(base_url)
        page_param = 'pi' if platform == 'trendyol' else 'sayfa'
        old_param = 'sayfa' if platform == 'trendyol' else 'pi'
        qs.pop(old_param, None)
        if page > 1:
            qs[page_param] = [str(page)]
        else:
            qs.pop(page_param, None)
        new_query = urlencode(qs, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    @staticmethod
    def _extract_hb_product_data_from_scripts(html: str) -> dict:
        product_map: dict[str, dict] = {}
        try:
            for m in re.finditer(r'"products":\[', html):
                start = m.start() + len('"products":')
                depth = 0
                end_idx = start
                for i, c in enumerate(html[start:start + 500000]):
                    if c == '[':
                        depth += 1
                    elif c == ']':
                        depth -= 1
                        if depth == 0:
                            end_idx = start + i + 1
                            break
                arr_json = html[start:end_idx]
                if len(arr_json) < 20:
                    continue
                try:
                    products = json.loads(arr_json)
                except json.JSONDecodeError:
                    continue
                if not isinstance(products, list):
                    continue
                for p in products:
                    if not isinstance(p, dict):
                        continue
                    pid = p.get('productId', '')
                    if not pid:
                        continue
                    brand = p.get('brand', '')
                    seller = ''
                    variants = p.get('variantList', [])
                    if variants and isinstance(variants, list):
                        for v in variants:
                            if not isinstance(v, dict):
                                continue
                            listing = v.get('listing', {})
                            if isinstance(listing, dict) and listing.get('merchantName'):
                                seller = listing['merchantName']
                                break
                    if pid not in product_map or brand:
                        product_map[pid] = {'brand': brand, 'seller': seller}
                if product_map:
                    break
        except Exception as e:
            logger.debug(f"Error extracting HB product data from scripts: {e}")
        return product_map

    def parse_hepsiburada_category(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        product_data_map = self._extract_hb_product_data_from_scripts(html)
        logger.info(f"Extracted brand/seller data for {len(product_data_map)} products from HB scripts")

        result = {
            'platform': 'hepsiburada',
            'breadcrumbs': [],
            'category_name': '',
            'total_products': 0,
            'products': [],
            'has_next_page': False,
        }

        bc_nav = soup.find('nav', {'aria-label': 'breadcrumb'}) or soup.find('div', class_=re.compile(r'breadcrumb', re.I))
        if bc_nav:
            links = bc_nav.find_all('a')
            for link in links:
                name = link.get_text(strip=True)
                href = link.get('href', '')
                if href and not href.startswith('http'):
                    href = f"https://www.hepsiburada.com{href}"
                if name:
                    result['breadcrumbs'].append({'name': name, 'url': href})
        else:
            bc_items = soup.find_all('li', class_=re.compile(r'breadcrumb', re.I))
            for item in bc_items:
                a = item.find('a')
                if a:
                    name = a.get_text(strip=True)
                    href = a.get('href', '')
                    if href and not href.startswith('http'):
                        href = f"https://www.hepsiburada.com{href}"
                    if name:
                        result['breadcrumbs'].append({'name': name, 'url': href})
                else:
                    name = item.get_text(strip=True)
                    if name:
                        result['breadcrumbs'].append({'name': name, 'url': url})

        title_el = soup.find('h1')
        if title_el:
            title_text = title_el.get_text(strip=True)
            count_match = re.search(r'\((\d[\d.]*)\s*ürün\)', title_text)
            if count_match:
                result['total_products'] = int(count_match.group(1).replace('.', ''))
                result['category_name'] = re.sub(r'\s*\(\d[\d.]*\s*ürün\)', '', title_text).strip()
            else:
                result['category_name'] = title_text

        if not result['total_products']:
            count_spans = soup.find_all(string=re.compile(r'\d+\s*ürün'))
            for s in count_spans:
                m = re.search(r'(\d[\d.]*)\s*ürün', s)
                if m:
                    result['total_products'] = int(m.group(1).replace('.', ''))
                    break

        product_cards = soup.find_all('li', attrs={'data-test-id': 'product-card-item'})
        if not product_cards:
            product_cards = soup.select('ul[class*="productListContent"] > li')
        if not product_cards:
            product_cards = soup.find_all('li', class_=re.compile(r'productListContent', re.I))
        if not product_cards:
            product_cards = soup.find_all('article', class_=re.compile(r'productCard', re.I))

        for card in product_cards:
            product = self._parse_hb_product_card(card, product_data_map)
            if product and product.get('name'):
                result['products'].append(product)

        next_btn = soup.find('a', string=re.compile(r'sonraki|ileri|next', re.I))
        if not next_btn:
            next_btn = soup.find('a', attrs={'rel': 'next'})
        if not next_btn:
            pagination_links = soup.find_all('a', href=re.compile(r'sayfa=\d+'))
            parsed_url = urlparse(url)
            current_qs = parse_qs(parsed_url.query)
            current_page = int(current_qs.get('sayfa', ['1'])[0])
            for link in pagination_links:
                href = link.get('href', '')
                m = re.search(r'sayfa=(\d+)', href)
                if m and int(m.group(1)) > current_page:
                    next_btn = link
                    break
        result['has_next_page'] = next_btn is not None

        load_more = soup.find(string=re.compile(r'Daha fazla ürün göster', re.I))
        if load_more:
            result['has_next_page'] = True

        return result

    def _parse_hb_product_card(self, card, product_data_map: dict = None) -> dict:
        product = {
            'name': '',
            'url': '',
            'image_url': '',
            'price': None,
            'original_price': None,
            'discount_percentage': None,
            'rating': None,
            'review_count': None,
            'brand': '',
            'is_sponsored': False,
            'campaign_text': '',
            'seller_name': '',
        }

        is_sponsored = card.find(string=re.compile(r'Reklam', re.I))
        if is_sponsored:
            product['is_sponsored'] = True

        link = card.find('a', href=True)
        if link:
            href = link.get('href', '')
            if 'adservice' in href or 'track?' in href:
                product['is_sponsored'] = True
                real_link = card.find('a', href=re.compile(r'hepsiburada\.com.*-pm-'))
                if real_link:
                    href = real_link['href']
            if href and not href.startswith('http'):
                href = f"https://www.hepsiburada.com{href}"
            product['url'] = href

        title_el = card.find('h3') or card.find('h2') or card.find('span', attrs={'data-test-id': 'product-card-name'})
        if title_el:
            product['name'] = title_el.get_text(strip=True)

        if not product['name']:
            title_a = card.find('a', {'title': True})
            if title_a:
                product['name'] = title_a.get('title', '').strip()

        if not product['name'] and link:
            product['name'] = link.get('title', '').strip()

        img = card.find('img')
        if img:
            product['image_url'] = img.get('src') or img.get('data-src') or img.get('loading') or ''

        price_spans = card.find_all(string=re.compile(r'^\d[\d.,]*\s*TL$'))
        prices = []
        for ps in price_spans:
            m = re.search(r'([\d.,]+)', ps)
            if m:
                price_val = m.group(1).replace('.', '').replace(',', '.')
                try:
                    prices.append(float(price_val))
                except ValueError:
                    pass

        if not prices:
            price_el = card.find(attrs={'data-test-id': re.compile(r'price', re.I)})
            if price_el:
                m = re.search(r'([\d.,]+)', price_el.get_text())
                if m:
                    price_val = m.group(1).replace('.', '').replace(',', '.')
                    try:
                        prices.append(float(price_val))
                    except ValueError:
                        pass

        if not prices:
            all_text = card.get_text()
            price_matches = re.findall(r'(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*TL', all_text)
            for pm in price_matches:
                price_val = pm.replace('.', '').replace(',', '.')
                try:
                    prices.append(float(price_val))
                except ValueError:
                    pass

        if prices:
            product['price'] = min(prices)
            if len(prices) > 1:
                product['original_price'] = max(prices)
                if product['original_price'] > product['price']:
                    product['discount_percentage'] = round(
                        (1 - product['price'] / product['original_price']) * 100, 1
                    )

        product_id = ''
        if product['url']:
            pid_match = re.search(r'-pm-([A-Za-z0-9]+)', product['url'])
            if pid_match:
                product_id = pid_match.group(1)

        if product_data_map and product_id and product_id in product_data_map:
            script_data = product_data_map[product_id]
            if script_data.get('brand'):
                product['brand'] = script_data['brand']
            if script_data.get('seller'):
                product['seller_name'] = script_data['seller']

        if not product['brand']:
            title_el_text = ''
            if title_el:
                title_el_text = title_el.get_text(strip=True)
            title_a = card.find('a', {'title': True})
            a_title_text = title_a.get('title', '').strip() if title_a else ''
            if title_el_text and a_title_text and title_el_text != a_title_text:
                if title_el_text.lower().endswith(a_title_text.lower()):
                    brand_candidate = title_el_text[:len(title_el_text) - len(a_title_text)].strip()
                    if brand_candidate and len(brand_candidate) < 40:
                        product['brand'] = brand_candidate

        if not product['seller_name']:
            seller_el = card.find('span', class_=re.compile(r'seller|merchant|storeName', re.I))
            if seller_el:
                product['seller_name'] = seller_el.get_text(strip=True)

        rating_el = card.find(string=re.compile(r'\d[.,]\d'))
        if rating_el:
            parent = rating_el.parent
            if parent:
                text = parent.get_text()
                m = re.search(r'(\d[.,]\d)\s*\((\d[\d.]*)\)', text)
                if m:
                    product['rating'] = float(m.group(1).replace(',', '.'))
                    product['review_count'] = int(m.group(2).replace('.', ''))
                else:
                    m2 = re.search(r'(\d[.,]\d)', text)
                    if m2:
                        product['rating'] = float(m2.group(1).replace(',', '.'))

        campaign_el = card.find(string=re.compile(r'Kampanya|indirim|Kupon|Al \d Öde', re.I))
        if campaign_el:
            product['campaign_text'] = campaign_el.strip()

        return product

    def parse_trendyol_category(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        result = {
            'platform': 'trendyol',
            'breadcrumbs': [],
            'category_name': '',
            'total_products': 0,
            'products': [],
            'has_next_page': False,
        }

        bc_el = soup.find('div', class_=re.compile(r'breadcrumb', re.I))
        if bc_el:
            links = bc_el.find_all('a')
            for link in links:
                name = link.get_text(strip=True)
                href = link.get('href', '')
                if href and not href.startswith('http'):
                    href = f"https://www.trendyol.com{href}"
                if name:
                    result['breadcrumbs'].append({'name': name, 'url': href})
            last_span = bc_el.find('span', class_=re.compile(r'last|active', re.I))
            if last_span:
                name = last_span.get_text(strip=True)
                if name:
                    result['breadcrumbs'].append({'name': name, 'url': url})

        title_el = soup.find('h1')
        if not title_el:
            title_el = soup.find('div', class_=re.compile(r'dscrptn', re.I))
        if title_el:
            result['category_name'] = title_el.get_text(strip=True)

        count_el = soup.find('div', class_=re.compile(r'dscrptn', re.I))
        if count_el:
            m = re.search(r'(\d[\d.]*)\s*(?:ürün|sonuç)', count_el.get_text())
            if m:
                result['total_products'] = int(m.group(1).replace('.', ''))

        if not result['total_products']:
            all_text = soup.get_text()
            m = re.search(r'(\d[\d.]*)\s*(?:ürün|sonuç)', all_text)
            if m:
                result['total_products'] = int(m.group(1).replace('.', ''))

        state_script = None
        for script in soup.find_all('script'):
            text = script.string or ''
            if '__SEARCH_APP_INITIAL_STATE__' in text:
                state_script = text
                break

        if state_script:
            m = re.search(r'__SEARCH_APP_INITIAL_STATE__\s*=\s*({.*?});?\s*(?:</script>|$)', state_script, re.DOTALL)
            if m:
                try:
                    state = json.loads(m.group(1))
                    products_data = state.get('products', state.get('searchData', {}).get('result', {}).get('products', []))
                    if isinstance(products_data, list):
                        for p in products_data:
                            product = {
                                'name': p.get('name', ''),
                                'url': f"https://www.trendyol.com{p['url']}" if p.get('url') else '',
                                'image_url': '',
                                'price': None,
                                'original_price': None,
                                'discount_percentage': None,
                                'rating': None,
                                'review_count': None,
                                'brand': p.get('brand', {}).get('name', '') if isinstance(p.get('brand'), dict) else str(p.get('brand', '')),
                                'is_sponsored': p.get('isSponsored', False) or p.get('sponsored', False),
                                'campaign_text': '',
                                'seller_name': p.get('merchantName', '') or p.get('seller', {}).get('name', '') if isinstance(p.get('seller'), dict) else '',
                            }

                            images = p.get('images', [])
                            if images:
                                img_url = images[0] if isinstance(images[0], str) else images[0].get('url', '')
                                if img_url and not img_url.startswith('http'):
                                    img_url = f"https://cdn.dsmcdn.com/{img_url}"
                                product['image_url'] = img_url

                            price_info = p.get('price', {})
                            if isinstance(price_info, dict):
                                product['price'] = price_info.get('sellingPrice') or price_info.get('discountedPrice') or price_info.get('originalPrice')
                                product['original_price'] = price_info.get('originalPrice')
                            elif isinstance(price_info, (int, float)):
                                product['price'] = price_info

                            if product['price'] and product['original_price'] and product['original_price'] > product['price']:
                                product['discount_percentage'] = round(
                                    (1 - product['price'] / product['original_price']) * 100, 1
                                )

                            rating_score = p.get('ratingScore', {})
                            if isinstance(rating_score, dict):
                                product['rating'] = rating_score.get('averageRating')
                                product['review_count'] = rating_score.get('totalCount') or rating_score.get('totalRatingCount')

                            campaigns = p.get('campaigns', []) or []
                            if campaigns:
                                texts = [c.get('name', '') or c.get('text', '') for c in campaigns if isinstance(c, dict)]
                                product['campaign_text'] = ' | '.join(t for t in texts if t)

                            if product['name']:
                                result['products'].append(product)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(f"Failed to parse Trendyol __SEARCH_APP_INITIAL_STATE__: {e}")

        if not result['products']:
            product_cards = soup.find_all('div', class_=re.compile(r'p-card-wrppr', re.I))
            for card in product_cards:
                product = self._parse_trendyol_product_card(card)
                if product and product.get('name'):
                    result['products'].append(product)

        parsed_url = urlparse(url)
        current_qs = parse_qs(parsed_url.query)
        current_page = int(current_qs.get('pi', current_qs.get('sayfa', ['1']))[0])

        if result['total_products'] > 0:
            per_page = max(len(result['products']), 24)
            total_pages = (result['total_products'] + per_page - 1) // per_page
            result['has_next_page'] = current_page < total_pages
        else:
            next_link = soup.find('a', attrs={'rel': 'next'})
            result['has_next_page'] = next_link is not None

        return result

    def _parse_trendyol_product_card(self, card) -> dict:
        product = {
            'name': '',
            'url': '',
            'image_url': '',
            'price': None,
            'original_price': None,
            'discount_percentage': None,
            'rating': None,
            'review_count': None,
            'brand': '',
            'is_sponsored': False,
            'campaign_text': '',
            'seller_name': '',
        }

        link = card.find('a', href=True)
        if link:
            href = link.get('href', '')
            if href and not href.startswith('http'):
                href = f"https://www.trendyol.com{href}"
            product['url'] = href

        brand_el = card.find('span', class_=re.compile(r'prdct-desc-cntnr-ttl', re.I))
        if brand_el:
            product['brand'] = brand_el.get_text(strip=True)

        name_el = card.find('span', class_=re.compile(r'prdct-desc-cntnr-name', re.I))
        if name_el:
            product['name'] = name_el.get_text(strip=True)
        elif link:
            product['name'] = link.get('title', '').strip()

        img = card.find('img')
        if img:
            product['image_url'] = img.get('src') or img.get('data-src') or ''

        price_el = card.find('div', class_=re.compile(r'prc-box-dscntd', re.I))
        if price_el:
            m = re.search(r'([\d.,]+)', price_el.get_text())
            if m:
                product['price'] = float(m.group(1).replace('.', '').replace(',', '.'))

        orig_price_el = card.find('div', class_=re.compile(r'prc-box-orgnl', re.I))
        if orig_price_el:
            m = re.search(r'([\d.,]+)', orig_price_el.get_text())
            if m:
                product['original_price'] = float(m.group(1).replace('.', '').replace(',', '.'))

        return product

    def parse_category_page(self, html: str, url: str) -> dict:
        platform = self.detect_platform(url)
        if platform == 'hepsiburada':
            return self.parse_hepsiburada_category(html, url)
        elif platform == 'trendyol':
            return self.parse_trendyol_category(html, url)
        else:
            return {
                'platform': 'other',
                'breadcrumbs': [],
                'category_name': 'Unknown',
                'total_products': 0,
                'products': [],
                'has_next_page': False,
            }
