import re
import ssl
import asyncio
import aiohttp
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import exists
from app.core.logger import price_monitor_logger as logger
from app.core.config import settings
from app.db.models import MonitoredProduct, SellerSnapshot, PriceMonitorTask


class PriceMonitorService:
    """Hepsiburada Listings API ve Campaign API'den satıcı fiyatlarını çeken servis"""
    
    LISTINGS_API_URL = "https://www.hepsiburada.com/api/v1/product/listings/{sku}"
    CAMPAIGN_API_URL = "https://obiwan-gw.hepsiburada.com/api/v2/Campaign/pdp"
    DEFAULT_MAX_CONCURRENT_REQUESTS = 17
    
    def __init__(self):
        self._semaphore = None  # Lazy initialization
        configured_limit = getattr(settings, "PRICE_MONITOR_MAX_CONCURRENT_REQUESTS", self.DEFAULT_MAX_CONCURRENT_REQUESTS)
        self.max_concurrent_requests = max(1, int(configured_limit or self.DEFAULT_MAX_CONCURRENT_REQUESTS))

    @property
    def api_key(self) -> str:
        return (settings.SCRAPER_API_KEY or "").strip()
    
    def _extract_sku_from_url(self, url: str) -> Optional[str]:
        """URL'den SKU çıkar: -p-SKU veya -pm-SKU formatından"""
        import re
        match = re.search(r'-p[m]?-([A-Z0-9]+)', url)
        if match:
            return match.group(1)
        return None
    
    
    def _has_campaign_in_tags(self, tag_list: List[Dict[str, Any]]) -> bool:
        """tagList'te indirim veya kampanya var mı kontrol et"""
        keywords = ['indirim', 'kampanya', 'sepet']
        for tag in tag_list:
            tag_id = tag.get('tagId', '').lower()
            if any(kw in tag_id for kw in keywords):
                return True
        return False
    
    def _has_percentage_discount(self, tag_list: List[Dict[str, Any]]) -> bool:
        """tagList'te yüzde indirim var mı kontrol et
        
        Yüzde indirim pattern: 'X-indirim' (örn: 5-indirim, 2-indirim)
        Hariç tutulan pattern'ler:
        - 'tl-ye': Kuponlar (örn: 500-tl-ye-50-tl-indirim)
        - 'X-urune': Ürün grubu kampanyaları (örn: 2-urune-1-indirim, 3-urune-2-indirim)
        
        Returns:
            True: Yüzde indirim varsa (Campaign API çağrılmalı)
            False: Kupon, ürün grubu kampanyası veya indirim yoksa
        """
        percentage_pattern = re.compile(r'-(\d+)-indirim$', re.IGNORECASE)
        exclude_pattern = re.compile(r'\d+-urune', re.IGNORECASE)
        
        for tag in tag_list:
            tag_id = tag.get('tagId', '').lower()
            
            if 'tl-ye' in tag_id:
                continue
            
            if exclude_pattern.search(tag_id):
                continue
            
            if percentage_pattern.search(tag_id):
                return True
        
        return False
    
    def _extract_percentage_discount_info(self, tag_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """tagList'ten yüzde indirim bilgisini çıkar
        
        Returns:
            {'discount_percentage': 5, 'tag_id': '59458991-cilakutusu-saticili-urunlerde-5-indirim'} veya None
        """
        percentage_pattern = re.compile(r'-(\d+)-indirim$', re.IGNORECASE)
        exclude_pattern = re.compile(r'\d+-urune', re.IGNORECASE)
        
        for tag in tag_list:
            tag_id = tag.get('tagId', '')
            tag_lower = tag_id.lower()
            
            if 'tl-ye' in tag_lower:
                continue
            
            if exclude_pattern.search(tag_lower):
                continue
            
            match = percentage_pattern.search(tag_lower)
            if match:
                return {
                    'discount_percentage': int(match.group(1)),
                    'tag_id': tag_id
                }
        
        return None

    async def fetch_campaign_price(self, sku: str, listing_id: str, merchant_id: str, merchant_name: str, price: float) -> Optional[Dict[str, Any]]:
        """Hepsiburada Campaign API'den gerçek kampanyalı fiyatı çek - Önce doğrudan, başarısız olursa ScraperAPI
        
        POST /api/v2/Campaign/pdp endpoint'ine minimal payload ile istek atar.
        discountedAmount değerini döndürür.
        
        Args:
            sku: Ürün SKU'su
            listing_id: Satıcının listing ID'si
            merchant_id: Satıcı ID'si
            merchant_name: Satıcı adı
            price: Listeleme fiyatı (amount olarak gönderilecek)
        
        Returns:
            {'discounted_price': float, 'campaign_text': str, 'campaigns': list} veya None
        """
        log_context = f"[SKU: {sku}] [Mağaza: {merchant_name}]"
        
        payload = {
            "customer": {"id": "", "tags": [], "gsmNumber": None, "uniqueDeviceId": None},
            "platform": "WebSite",
            "appKey": "WebSite",
            "product": {
                "sku": sku,
                "listingId": listing_id,
                "merchant": {
                    "id": merchant_id,
                    "name": merchant_name,
                    "isCampaignContractAccepted": True
                },
                "amount": price
            }
        }
        
        result = await self._call_campaign_api_direct(payload, log_context, price)
        if result:
            return result
        
        logger.debug(f"{log_context} Doğrudan Campaign API başarısız, ScraperAPI proxy deneniyor...")
        return await self._call_campaign_api_via_scraper(payload, log_context, price)
    
    async def _call_campaign_api_direct(self, payload: dict, log_context: str, price: float) -> Optional[Dict[str, Any]]:
        """Campaign API'ye doğrudan istek at"""
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://www.hepsiburada.com',
            'Referer': 'https://www.hepsiburada.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.CAMPAIGN_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        return await self._parse_campaign_response(await resp.json(), log_context, price)
                    elif resp.status == 403:
                        logger.debug(f"{log_context} Doğrudan Campaign API 403 - IP engeli")
                        return None
                    else:
                        logger.debug(f"{log_context} Doğrudan Campaign API hata: {resp.status}")
                        return None
        except Exception as e:
            logger.debug(f"{log_context} Doğrudan Campaign API exception: {type(e).__name__}")
            return None
    
    async def _call_campaign_api_via_scraper(self, payload: dict, log_context: str, price: float) -> Optional[Dict[str, Any]]:
        """Campaign API'ye ScraperAPI proxy üzerinden istek at"""
        import json
        
        api_key = self.api_key
        if not api_key:
            logger.warning(f"{log_context} ScraperAPI key missing, campaign fallback skipped")
            return None

        encoded_url = urllib.parse.quote(self.CAMPAIGN_API_URL, safe='')
        api_url = f"https://api.scraperapi.com?api_key={api_key}&url={encoded_url}"
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://www.hepsiburada.com',
            'Referer': 'https://www.hepsiburada.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=45)
                ) as resp:
                    if resp.status == 200:
                        return await self._parse_campaign_response(await resp.json(), log_context, price)
                    else:
                        error_text = await resp.text()
                        logger.warning(f"{log_context} ScraperAPI Campaign hatası: {resp.status} | {error_text[:100]}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"{log_context} ScraperAPI Campaign zaman aşımı (45s)")
            return None
        except Exception as e:
            logger.error(f"{log_context} ScraperAPI Campaign hata: {type(e).__name__}: {e}")
            return None
    
    async def _parse_campaign_response(self, data: dict, log_context: str, price: float) -> Optional[Dict[str, Any]]:
        """Campaign API yanıtını parse et"""
        evaluate_result = data.get('campaignEvaluateResult', {}).get('evaluateResult', {})
        
        if evaluate_result:
            discounted_price = evaluate_result.get('discountedAmount')
            final_price = evaluate_result.get('finalPriceOnSale')
            campaign_text = evaluate_result.get('campaignText', '')
            campaigns = evaluate_result.get('campaigns', [])
            
            if discounted_price:
                logger.info(f"{log_context} Campaign API: İndirimli fiyat {discounted_price} TL (orijinal: {price} TL) - {campaign_text}")
                return {
                    'discounted_price': discounted_price,
                    'final_price': final_price,
                    'campaign_text': campaign_text,
                    'campaigns': campaigns
                }
            else:
                logger.debug(f"{log_context} Campaign API: discountedAmount yok")
        else:
            logger.debug(f"{log_context} Campaign API: evaluateResult boş")
        return None

    async def fetch_listings(self, sku: str) -> Dict[str, Any]:
        """Tek bir SKU için listings API'sinden satıcı verilerini çek.

        Returns:
            {
                "success": bool,
                "data": Optional[Dict[str, Any]],
                "error_type": Optional[str],  # auth_error | upstream_error | no_data
                "status_code": Optional[int],
            }
        """
        api_key = self.api_key
        if not api_key:
            logger.error(f"Listings API auth_error for {sku}: ScraperAPI key missing")
            return {
                "success": False,
                "data": None,
                "error_type": "auth_error",
                "status_code": None,
            }

        target_url = self.LISTINGS_API_URL.format(sku=sku)
        encoded_url = urllib.parse.quote(target_url, safe='')
        api_url = f"https://api.scraperapi.com?api_key={api_key}&url={encoded_url}"
        
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
                            return {
                                "success": True,
                                "data": data['data'],
                                "error_type": None,
                                "status_code": 200,
                            }
                        logger.warning(
                            f"Listings API upstream_error for {sku}: unexpected payload statusCode={data.get('statusCode')}"
                        )
                        return {
                            "success": False,
                            "data": None,
                            "error_type": "upstream_error",
                            "status_code": data.get('statusCode'),
                        }
                    if resp.status in (401, 403):
                        logger.warning(f"Listings API auth_error for {sku}: status {resp.status}")
                        return {
                            "success": False,
                            "data": None,
                            "error_type": "auth_error",
                            "status_code": resp.status,
                        }
                    if resp.status in (404, 410):
                        logger.warning(f"Listings API no_data for {sku}: status {resp.status}")
                        return {
                            "success": False,
                            "data": None,
                            "error_type": "no_data",
                            "status_code": resp.status,
                        }
                    logger.warning(f"Listings API upstream_error for {sku}: status {resp.status}")
                    return {
                        "success": False,
                        "data": None,
                        "error_type": "upstream_error",
                        "status_code": resp.status,
                    }
        except asyncio.TimeoutError:
            logger.error(f"Listings API upstream_error for {sku}: timeout")
            return {
                "success": False,
                "data": None,
                "error_type": "upstream_error",
                "status_code": None,
            }
        except Exception as e:
            logger.error(f"Listings API upstream_error for {sku}: {type(e).__name__}: {e}")
            return {
                "success": False,
                "data": None,
                "error_type": "upstream_error",
                "status_code": None,
            }
    
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
            tag_list = listing.get('tagList', [])
            
            seller = {
                'merchant_id': listing.get('merchantId'),
                'listing_id': listing.get('listingId'),
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
            
            seller['raw_tag_list'] = tag_list
            seller['has_campaign_tag'] = self._has_campaign_in_tags(tag_list)
            seller['has_percentage_discount'] = self._has_percentage_discount(tag_list)
            
            discount_info = self._extract_percentage_discount_info(tag_list)
            if discount_info:
                seller['discount_percentage'] = discount_info['discount_percentage']
                seller['discount_tag_id'] = discount_info['tag_id']
            
            if tag_list:
                seller['campaigns'] = self._parse_campaign_tags(tag_list)
            else:
                seller['campaigns'] = []
            
            sellers.append(seller)
        
        return sellers
    
    async def fetch_product_data(self, product: MonitoredProduct) -> Dict[str, Any]:
        """Tek bir ürün için HTTP isteklerini yap (DB işlemi yok) - Paralel çalışır"""
        sku = product.sku
        if sku.startswith('SKU: '):
            sku = sku.replace('SKU: ', '')
        
        result = {
            'product_id': product.id,
            'sku': sku,
            'success': False,
            'inactive': False,
            'sellers': [],
            'error': None
        }
        
        try:
            fetch_result = await self.fetch_listings(sku)
            if not fetch_result.get('success'):
                error_type = fetch_result.get('error_type') or 'upstream_error'
                result['error'] = error_type
                if error_type == 'no_data':
                    result['inactive'] = True
                    logger.warning(f"No data for SKU {sku} - will be marked inactive")
                else:
                    logger.warning(
                        f"Fetch failed for SKU {sku}: error_type={error_type}, status={fetch_result.get('status_code')} - keeping current active state"
                    )
                return result
            
            data = fetch_result['data']
            
            sellers = self.parse_listings(data)
            if not sellers:
                result['inactive'] = True
                result['error'] = 'no_sellers'
                logger.warning(f"No sellers for SKU {sku} - will be marked inactive")
                return result
            
            percentage_discount_sellers = [s for s in sellers if s.get('has_percentage_discount', False)]
            if percentage_discount_sellers:
                seller_details = [f"{s.get('merchant_name')} (%{s.get('discount_percentage', '?')} - {s.get('discount_tag_id', 'N/A')})" for s in percentage_discount_sellers]
                logger.info(f"[SKU: {sku}] {len(percentage_discount_sellers)} satıcıda yüzde indirim bulundu: {', '.join(seller_details)}")
                
                success_count = 0
                fail_count = 0
                for seller in percentage_discount_sellers:
                    try:
                        listing_id = seller.get('listing_id')
                        merchant_id = seller.get('merchant_id')
                        merchant_name = seller.get('merchant_name')
                        price = seller.get('price')
                        discount_tag = seller.get('discount_tag_id', 'N/A')
                        
                        if not all([listing_id, merchant_id, merchant_name, price]):
                            logger.warning(f"[SKU: {sku}] [Mağaza: {merchant_name}] Campaign API için gerekli bilgiler eksik")
                            fail_count += 1
                            continue
                        
                        campaign_data = await self.fetch_campaign_price(
                            sku=sku,
                            listing_id=listing_id,
                            merchant_id=merchant_id,
                            merchant_name=merchant_name,
                            price=price
                        )
                        
                        if campaign_data and campaign_data.get('discounted_price'):
                            seller['campaign_price'] = campaign_data['discounted_price']
                            seller['original_price_from_page'] = seller['price']
                            seller['price'] = campaign_data['discounted_price']
                            seller['campaign_text'] = campaign_data.get('campaign_text', '')
                            success_count += 1
                        else:
                            logger.warning(f"[SKU: {sku}] [Mağaza: {merchant_name}] Campaign API başarısız - discounted_price yok (tag: {discount_tag})")
                            fail_count += 1
                    except Exception as e:
                        logger.error(f"[SKU: {sku}] [Mağaza: {seller.get('merchant_name', 'N/A')}] Campaign API hatası: {type(e).__name__}: {e}")
                        fail_count += 1
                
                if fail_count > 0:
                    logger.info(f"[SKU: {sku}] Campaign API sonuç: {success_count} başarılı, {fail_count} başarısız")
            
            result['success'] = True
            result['sellers'] = sellers
            logger.info(f"Fetched {len(sellers)} sellers for SKU {sku}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error fetching product {sku}: {e}")
        
        return result
    
    def save_product_result(self, db: Session, product: MonitoredProduct, result: Dict[str, Any]) -> bool:
        """Fetch sonucunu DB'ye kaydet (sıralı çalışır)"""
        if result['inactive']:
            product.is_active = False
            product.last_fetched_at = datetime.utcnow()
            return False
        
        if not result['success']:
            return False
        
        if not product.is_active:
            product.is_active = True
            logger.info(f"SKU {result['sku']} reactivated - sellers found")
        
        for seller in result['sellers']:
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
        return True
    
    async def fetch_all_products(self, db: Session, task: PriceMonitorTask, product_ids: List[str] = None, platform: str = "hepsiburada", fetch_type: str = "active"):
        """Belirli platform için izlenen ürünlerin satıcı verilerini çek - PARALEL İŞLEME
        
        Args:
            fetch_type: "active" (varsayılan), "last_inactive" (önceki fetch'te inactive olanlar), "inactive" (tüm inaktif ürünler)
        """
        has_sellers_subquery = exists().where(
            SellerSnapshot.monitored_product_id == MonitoredProduct.id
        )
        
        if fetch_type == "last_inactive":
            last_task = db.query(PriceMonitorTask).filter(
                PriceMonitorTask.platform == platform,
                PriceMonitorTask.status == "completed"
            ).order_by(PriceMonitorTask.completed_at.desc()).first()
            
            if last_task and last_task.last_inactive_skus:
                products = db.query(MonitoredProduct).filter(
                    MonitoredProduct.sku.in_(last_task.last_inactive_skus),
                    MonitoredProduct.platform == platform
                ).all()
                logger.info(f"Last inactive fetch: {len(last_task.last_inactive_skus)} SKU hedefleniyor")
            else:
                products = []
                logger.warning("No last inactive SKUs found")
        elif fetch_type == "inactive":
            products = db.query(MonitoredProduct).filter(
                MonitoredProduct.platform == platform,
                MonitoredProduct.is_active == False
            ).all()
            logger.info(f"Inactive fetch: {len(products)} ürün")
        else:
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
        task.fetch_type = fetch_type
        task.status = "running"
        task.last_inactive_skus = []
        db.commit()
        
        if not products:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            db.commit()
            logger.info("No products to process")
            return
        
        logger.info(f"PARALEL İŞLEME BAŞLIYOR: {len(products)} ürün, {self.max_concurrent_requests} eşzamanlı istek")
        
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        completed = 0
        failed = 0
        inactive_skus = []
        auth_failed_skus = []
        upstream_failed_skus = []
        product_map = {str(p.id): p for p in products}
        
        async def fetch_with_semaphore(product: MonitoredProduct) -> Dict[str, Any]:
            """Semaphore ile rate-limited paralel fetch"""
            async with semaphore:
                result = await self.fetch_product_data(product)
                await asyncio.sleep(0.3)
                return result
        
        batch_size = 50
        total_batches = (len(products) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            db.refresh(task)
            if task.stop_requested:
                logger.info(f"Stop requested at batch {batch_idx + 1}/{total_batches}")
                task.last_processed_index = batch_idx * batch_size
                task.status = "stopped"
                task.completed_at = datetime.utcnow()
                task.last_inactive_skus = inactive_skus
                db.commit()
                return
            
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(products))
            batch_products = products[start_idx:end_idx]
            
            logger.info(f"Batch {batch_idx + 1}/{total_batches}: {len(batch_products)} ürün paralel işleniyor...")
            
            tasks = [fetch_with_semaphore(p) for p in batch_products]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Batch exception: {result}")
                    failed += 1
                    continue
                
                product = product_map.get(str(result['product_id']))
                if not product:
                    continue
                
                if result['inactive']:
                    inactive_skus.append(result['sku'])
                    failed += 1
                    self.save_product_result(db, product, result)
                elif result['success']:
                    completed += 1
                    self.save_product_result(db, product, result)
                else:
                    failed += 1
                    if result.get('error') == 'auth_error':
                        auth_failed_skus.append(result['sku'])
                    elif result.get('error') == 'upstream_error':
                        upstream_failed_skus.append(result['sku'])
            
            db.commit()
            
            task.completed_products = completed
            task.failed_products = failed
            task.last_processed_index = end_idx
            if auth_failed_skus or upstream_failed_skus:
                task.error_message = (
                    f"auth_errors={len(auth_failed_skus)};upstream_errors={len(upstream_failed_skus)}"
                )
            db.commit()
            
            logger.info(
                f"Batch {batch_idx + 1} tamamlandı: toplam {completed} başarılı, {failed} başarısız, "
                f"{len(inactive_skus)} inactive, {len(auth_failed_skus)} auth_error, {len(upstream_failed_skus)} upstream_error"
            )
        
        task.completed_products = completed
        task.failed_products = failed
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.last_inactive_skus = inactive_skus
        if auth_failed_skus or upstream_failed_skus:
            task.error_message = (
                f"auth_errors={len(auth_failed_skus)};upstream_errors={len(upstream_failed_skus)}"
            )
        db.commit()
        
        logger.info(
            f"Fetch task completed: {completed} success, {failed} failed, {len(inactive_skus)} marked inactive, "
            f"{len(auth_failed_skus)} auth_error, {len(upstream_failed_skus)} upstream_error"
        )

    async def fetch_and_save_product(self, db: Session, product: MonitoredProduct) -> bool:
        """Tek bir ürünü çekip DB'ye kaydet."""
        try:
            result = await self.fetch_product_data(product)
            success = self.save_product_result(db, product, result)
            db.commit()
            return success
        except Exception as e:
            logger.error(f"Single fetch error for SKU {product.sku}: {e}")
            db.rollback()
            return False


price_monitor_service = PriceMonitorService()
