import os
import re
import ssl
import random
import asyncio
import aiohttp
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.core.logger import price_monitor_logger as logger
from app.db.models import MonitoredProduct, SellerSnapshot, PriceMonitorTask


class PriceMonitorService:
    """Hepsiburada listings API'den satıcı fiyatlarını çeken servis"""
    
    LISTINGS_API_URL = "https://www.hepsiburada.com/api/v1/product/listings/{sku}"
    
    def __init__(self):
        self.api_key = os.environ.get('SCRAPPER_API', '')
        if not self.api_key:
            try:
                with open('/etc/secrets/SCRAPPER_API', 'r') as f:
                    self.api_key = f.read().strip()
            except:
                pass
    
    def _extract_sku_from_url(self, url: str) -> Optional[str]:
        """URL'den SKU çıkar: -p-SKU veya -pm-SKU formatından"""
        import re
        match = re.search(r'-p[m]?-([A-Z0-9]+)', url)
        if match:
            return match.group(1)
        return None
    
    async def fetch_seller_campaign_price(self, product_url: str, seller_name: str, sku: str = None) -> Optional[Dict[str, Any]]:
        """Satıcıya özel ürün sayfasından kampanyalı fiyatı kazı
        
        URL format: {product_url}?magaza={url_encoded_seller_name}
        Hedef element: data-test-id="checkout-price" veya data-test-id="price"
        """
        encoded_seller = urllib.parse.quote(seller_name, safe='')
        seller_url = f"{product_url}?magaza={encoded_seller}"
        
        encoded_url = urllib.parse.quote(seller_url, safe='')
        api_url = f"https://api.scraperapi.com?api_key={self.api_key}&url={encoded_url}"
        
        log_context = f"[SKU: {sku or 'N/A'}] [Mağaza: {seller_name}]"
        logger.debug(f"{log_context} Kampanya fiyatı çekiliyor: {seller_url}")
        
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    api_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        result = self._parse_campaign_price_from_html(html, seller_name)
                        if result and result.get('campaign_price'):
                            logger.info(f"{log_context} Kampanya fiyatı bulundu: {result['campaign_price']} TL (orijinal: {result.get('original_price', 'N/A')} TL)")
                        else:
                            logger.warning(f"{log_context} Sayfa çekildi ama kampanya fiyatı bulunamadı")
                        return result
                    else:
                        error_text = await resp.text()
                        error_preview = error_text[:200] if error_text else "Boş yanıt"
                        logger.warning(f"{log_context} ScraperAPI hatası: status {resp.status} | URL: {seller_url} | Yanıt: {error_preview}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"{log_context} Zaman aşımı (60s) | URL: {seller_url}")
            return None
        except Exception as e:
            logger.error(f"{log_context} Hata: {type(e).__name__}: {e} | URL: {seller_url}")
            return None
    
    def _parse_campaign_price_from_html(self, html: str, seller_name: str) -> Optional[Dict[str, Any]]:
        """HTML'den kampanyalı fiyatı parse et
        
        Hedef elementler:
        - data-test-id="checkout-price" -> Sepete özel fiyat
        - data-test-id="prev-price" -> Orijinal fiyat
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            'campaign_price': None,
            'original_price': None,
            'has_campaign': False
        }
        
        checkout_price_div = soup.find('div', {'data-test-id': 'checkout-price'})
        if checkout_price_div:
            price_divs = checkout_price_div.find_all('div')
            for div in price_divs:
                text = div.get_text(strip=True)
                if 'TL' in text and not 'özel' in text.lower():
                    price = self._parse_price_text(text)
                    if price:
                        result['campaign_price'] = price
                        result['has_campaign'] = True
                        break
        
        prev_price_div = soup.find('div', {'data-test-id': 'prev-price'})
        if prev_price_div:
            price_span = prev_price_div.find('span')
            if price_span:
                text = price_span.get_text(strip=True)
                price = self._parse_price_text(text)
                if price:
                    result['original_price'] = price
        
        if not result['campaign_price']:
            price_div = soup.find('div', {'data-test-id': 'price'})
            if price_div:
                price_spans = price_div.find_all('span')
                for span in price_spans:
                    text = span.get_text(strip=True)
                    if 'TL' in text:
                        price = self._parse_price_text(text)
                        if price:
                            result['campaign_price'] = price
                            result['has_campaign'] = True
                            break
        
        if result['campaign_price']:
            return result
        
        return None
    
    def _parse_price_text(self, text: str) -> Optional[float]:
        """Fiyat metnini float'a çevir: '1.139,05 TL' -> 1139.05"""
        try:
            clean = re.sub(r'[^\d.,]', '', text)
            clean = clean.replace('.', '').replace(',', '.')
            return float(clean)
        except:
            return None
    
    def _has_campaign_in_tags(self, tag_list: List[Dict[str, Any]]) -> bool:
        """tagList'te indirim veya kampanya var mı kontrol et"""
        keywords = ['indirim', 'kampanya', 'sepet']
        for tag in tag_list:
            tag_id = tag.get('tagId', '').lower()
            if any(kw in tag_id for kw in keywords):
                return True
        return False

    async def fetch_listings(self, sku: str) -> Optional[Dict[str, Any]]:
        """Tek bir SKU için listings API'sinden satıcı verilerini çek - ScraperAPI HTTP API"""
        
        target_url = self.LISTINGS_API_URL.format(sku=sku)
        encoded_url = urllib.parse.quote(target_url, safe='')
        api_url = f"https://api.scraperapi.com?api_key={self.api_key}&url={encoded_url}"
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    api_url,
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('statusCode') == 200 and 'data' in data:
                            return data['data']
                    else:
                        logger.warning(f"Listings API error for {sku}: status {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching listings for {sku}: {e}")
            return None
    
    def _parse_campaign_tags(self, tag_list: List[Dict[str, Any]]) -> List[str]:
        """tagList'ten indirim ve kampanya tag'lerini filtrele ve okunabilir formata çevir"""
        campaigns = []
        keywords = ['indirim', 'kampanya']
        
        for tag in tag_list:
            tag_id = tag.get('tagId', '')
            tag_lower = tag_id.lower()
            
            if any(kw in tag_lower for kw in keywords):
                readable = self._make_tag_readable(tag_id)
                if readable and readable not in campaigns:
                    campaigns.append(readable)
        
        return campaigns
    
    def _make_tag_readable(self, tag_id: str) -> str:
        """Tag ID'yi okunabilir formata çevir"""
        import re
        
        clean_tag = re.sub(r'^[0-9]+-', '', tag_id)
        
        readable = clean_tag.replace('-', ' ')
        
        readable = re.sub(r'(\d+)\s*tl\s*ye\s*(\d+)\s*tl', r'\1 TL üzeri \2 TL', readable, flags=re.IGNORECASE)
        
        readable = re.sub(r'(\d+)\s*indirim', r'%\1 İndirim', readable, flags=re.IGNORECASE)
        readable = re.sub(r'(\d+)\s*kampanya', r'%\1 Kampanya', readable, flags=re.IGNORECASE)
        
        words = readable.split()
        result_words = []
        for word in words:
            if word.upper() == 'TL' or word.startswith('%'):
                result_words.append(word)
            elif word.lower() in ['ve', 'ile', 'için', 'den', 'dan']:
                result_words.append(word.lower())
            else:
                result_words.append(word.capitalize())
        
        readable = ' '.join(result_words)
        readable = readable.replace('Indirim', 'İndirim')
        readable = readable.replace('Tl', 'TL')
        
        return readable.strip()
    
    def parse_listings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API yanıtından satıcı bilgilerini parse et"""
        sellers = []
        listings = data.get('listings', [])
        
        for listing in listings:
            merchant_info = listing.get('merchantInfo', {})
            seller = {
                'merchant_id': listing.get('merchantId'),
                'merchant_name': listing.get('merchantName'),
                'merchant_logo': listing.get('logo'),
                'merchant_url_postfix': merchant_info.get('urlPostfix'),
                'merchant_city': listing.get('merchantCity'),
                'price': listing.get('price', {}).get('value'),
                'original_price': listing.get('originalPrice', {}).get('value'),
                'minimum_price': listing.get('minimumPrice', {}).get('value'),
                'discount_rate': listing.get('discountRate', 0),
                'stock_quantity': listing.get('quantity'),
                'buybox_order': listing.get('buyboxOrder'),
                'free_shipping': listing.get('freeShipping', False),
                'fast_shipping': listing.get('fastShipping', False),
                'is_fulfilled_by_hb': listing.get('isFulfilledByHB', False),
            }
            
            rating_summary = listing.get('ratingSummary', {})
            if rating_summary:
                seller['merchant_rating'] = rating_summary.get('lifetimeRating')
                seller['merchant_rating_count'] = rating_summary.get('ratingQuantity')
            
            tag_list = listing.get('tagList', [])
            seller['raw_tag_list'] = tag_list
            seller['has_campaign_tag'] = self._has_campaign_in_tags(tag_list)
            if tag_list:
                seller['campaigns'] = self._parse_campaign_tags(tag_list)
            else:
                seller['campaigns'] = []
            
            sellers.append(seller)
        
        return sellers
    
    async def fetch_and_save_product(self, db: Session, product: MonitoredProduct) -> bool:
        """Tek bir ürün için satıcı verilerini çek ve kaydet"""
        sku = product.sku
        if sku.startswith('SKU: '):
            sku = sku.replace('SKU: ', '')
        
        data = await self.fetch_listings(sku)
        if not data:
            product.is_active = False
            product.last_fetched_at = datetime.utcnow()
            db.commit()
            logger.warning(f"No data for SKU {sku} - marked as inactive")
            return False
        
        sellers = self.parse_listings(data)
        if not sellers:
            product.is_active = False
            product.last_fetched_at = datetime.utcnow()
            db.commit()
            logger.warning(f"No sellers for SKU {sku} - marked as inactive")
            return False
        
        if not product.is_active:
            product.is_active = True
            logger.info(f"SKU {sku} reactivated - sellers found")
        
        campaign_sellers = [s for s in sellers if s.get('has_campaign_tag', False)]
        if campaign_sellers and product.product_url:
            logger.info(f"[SKU: {sku}] {len(campaign_sellers)} satıcıda kampanya bulundu, gerçek fiyatlar çekiliyor...")
            for seller in campaign_sellers:
                try:
                    campaign_data = await self.fetch_seller_campaign_price(
                        product.product_url, 
                        seller['merchant_name'],
                        sku=sku
                    )
                    if campaign_data and campaign_data.get('campaign_price'):
                        seller['campaign_price'] = campaign_data['campaign_price']
                        seller['original_price_from_page'] = campaign_data.get('original_price')
                        seller['price'] = campaign_data['campaign_price']
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"[SKU: {sku}] [Mağaza: {seller['merchant_name']}] Beklenmeyen hata: {type(e).__name__}: {e}")
        
        for seller in sellers:
            snapshot = SellerSnapshot(
                monitored_product_id=product.id,
                merchant_id=seller['merchant_id'],
                merchant_name=seller['merchant_name'],
                merchant_logo=seller.get('merchant_logo'),
                merchant_url_postfix=seller.get('merchant_url_postfix'),
                merchant_rating=seller.get('merchant_rating'),
                merchant_rating_count=seller.get('merchant_rating_count'),
                merchant_city=seller.get('merchant_city'),
                price=seller['price'],
                original_price=seller.get('original_price'),
                minimum_price=seller.get('minimum_price'),
                discount_rate=seller.get('discount_rate'),
                stock_quantity=seller.get('stock_quantity'),
                buybox_order=seller.get('buybox_order'),
                free_shipping=seller.get('free_shipping', False),
                fast_shipping=seller.get('fast_shipping', False),
                is_fulfilled_by_hb=seller.get('is_fulfilled_by_hb', False),
                campaigns=seller.get('campaigns', []),
                campaign_price=seller.get('campaign_price'),
                snapshot_date=datetime.utcnow()
            )
            db.add(snapshot)
        
        product.last_fetched_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Saved {len(sellers)} sellers for SKU {sku}")
        return True
    
    async def fetch_all_products(self, db: Session, task: PriceMonitorTask, product_ids: List[str] = None, platform: str = "hepsiburada"):
        """Belirli platform için izlenen ürünlerin satıcı verilerini çek"""
        if product_ids:
            products = db.query(MonitoredProduct).filter(
                MonitoredProduct.id.in_(product_ids),
                MonitoredProduct.platform == platform,
                MonitoredProduct.is_active == True
            ).all()
        else:
            products = db.query(MonitoredProduct).filter(
                MonitoredProduct.platform == platform,
                MonitoredProduct.is_active == True
            ).all()
        
        task.total_products = len(products)
        task.status = "running"
        db.commit()
        
        completed = 0
        failed = 0
        
        for product in products:
            db.refresh(task)
            if task.stop_requested:
                logger.info(f"Stop requested, finishing after {completed} products")
                task.status = "stopped"
                task.completed_at = datetime.utcnow()
                db.commit()
                return
            
            try:
                success = await self.fetch_and_save_product(db, product)
                if success:
                    completed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Error processing product {product.sku}: {e}")
                failed += 1
            
            task.completed_products = completed
            task.failed_products = failed
            db.commit()
            
            await asyncio.sleep(1)
        
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Fetch task completed: {completed} success, {failed} failed")


price_monitor_service = PriceMonitorService()
