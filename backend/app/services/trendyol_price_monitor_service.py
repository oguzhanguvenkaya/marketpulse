import os
import ssl
import random
import asyncio
import aiohttp
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.core.logger import price_monitor_logger as logger
from app.db.models import MonitoredProduct, SellerSnapshot, PriceMonitorTask


class TrendyolPriceMonitorService:
    """Trendyol ürün sayfasından other-merchants bölümündeki satıcı verilerini çeken servis"""
    
    MAX_CONCURRENT_REQUESTS = 5
    
    def __init__(self):
        self.api_key = os.environ.get('SCRAPPER_API', '')
        self._semaphore = None
        if not self.api_key:
            try:
                with open('/etc/secrets/SCRAPPER_API', 'r') as f:
                    self.api_key = f.read().strip()
            except:
                pass
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Türk lirası formatındaki fiyatı parse et: 2.611,55 TL -> 2611.55"""
        if not price_text:
            return None
        try:
            cleaned = price_text.replace('TL', '').strip()
            cleaned = cleaned.replace('.', '').replace(',', '.')
            return float(cleaned)
        except:
            return None
    
    def _extract_merchant_id(self, href: str) -> Optional[str]:
        """URL'den merchant ID çıkar: /sr?mid=410074 -> 410074"""
        if not href:
            return None
        match = re.search(r'mid=(\d+)', href)
        if match:
            return match.group(1)
        return None
    
    async def fetch_product_page(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """ScraperAPI ile Trendyol ürün sayfasını çek - render=true mod (JavaScript için gerekli)"""
        session_num = random.randint(1, 999999)
        proxy_url = 'http://proxy-server.scraperapi.com:8001'
        proxy_user = f'scraperapi.render=true.session_number={session_num}'
        proxy_pass = self.api_key
        
        proxy_auth = aiohttp.BasicAuth(proxy_user, proxy_pass)
        
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.trendyol.com/'
        }
        
        try:
            async with session.get(
                url, 
                proxy=proxy_url, 
                proxy_auth=proxy_auth, 
                headers=headers, 
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    if 'other-merchant' in html or 'slider__slide' in html:
                        logger.debug("Trendyol page fetched successfully")
                        return html
                    else:
                        logger.debug("Trendyol page fetched but no other-merchants section found")
                        return html
                else:
                    logger.warning(f"Trendyol page error: status {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching Trendyol page: {e}")
            return None
    
    def parse_other_merchants(self, html: str) -> List[Dict[str, Any]]:
        """HTML'den other-seller bölümündeki satıcı bilgilerini parse et (Trendyol'un yeni yapısı)"""
        sellers = []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        containers = soup.find_all(class_=lambda x: x and 'other-seller-item-other-seller-container' in x)
        
        if not containers:
            containers = soup.find_all(class_=lambda x: x and 'other-merchant-item-box' in x)
        
        if not containers:
            other_merchants = soup.find(id='other-merchants')
            if other_merchants:
                containers = other_merchants.find_all('div', {'data-testid': 'slide'})
        
        logger.debug(f"Found {len(containers)} seller containers")
        
        for idx, container in enumerate(containers):
            seller = {
                'buybox_order': idx + 1,
                'merchant_id': None,
                'merchant_name': None,
                'merchant_rating': None,
                'price': None,
                'original_price': None,
                'discount_rate': None,
                'free_shipping': False,
                'fast_shipping': False,
                'delivery_info': None,
                'campaign_info': None
            }
            
            link = container.find('a', href=lambda x: x and 'mid=' in x)
            if link:
                seller['merchant_name'] = link.get_text(strip=True)
                seller['merchant_url_postfix'] = link.get('href')
                seller['merchant_id'] = self._extract_merchant_id(link.get('href'))
            
            score_elem = container.find(class_=lambda x: x and 'score' in str(x).lower())
            if score_elem:
                try:
                    score_text = score_elem.get_text(strip=True)
                    seller['merchant_rating'] = float(score_text.replace(',', '.'))
                except:
                    pass
            
            new_price_elem = container.find(class_='new-price')
            if new_price_elem:
                seller['price'] = self._parse_price(new_price_elem.get_text(strip=True))
            
            old_price_elem = container.find(class_='old-price')
            if old_price_elem:
                seller['original_price'] = self._parse_price(old_price_elem.get_text(strip=True))
            
            if not seller['price']:
                for price_elem in container.find_all(class_=lambda x: x and 'price' in str(x).lower()):
                    text = price_elem.get_text(strip=True)
                    if 'TL' in text:
                        parsed = self._parse_price(text)
                        if parsed:
                            seller['price'] = parsed
                            break
            
            if seller['price'] and seller['original_price']:
                seller['discount_rate'] = round((1 - seller['price'] / seller['original_price']) * 100, 1)
            
            campaign_elem = container.find(class_=lambda x: x and 'campaign-price-info' in str(x))
            if campaign_elem:
                seller['campaign_info'] = campaign_elem.get_text(strip=True)
            
            shipping_elems = container.find_all(class_=lambda x: x and ('cargo' in str(x).lower() or 'kargo' in str(x).lower()))
            for elem in shipping_elems:
                text = elem.get_text(strip=True).lower()
                if 'bedava' in text or 'ücretsiz' in text or 'free' in text:
                    seller['free_shipping'] = True
                    break
            
            if seller['merchant_name']:
                sellers.append(seller)
                logger.debug(f"Parsed seller: {seller['merchant_name']} - {seller['price']} TL")
        
        return sellers
    
    async def fetch_single_product(self, product: MonitoredProduct, http_session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Tek bir ürün için HTTP isteği yap ve sonucu döndür (thread-safe)"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        async with self._semaphore:
            html = await self.fetch_product_page(product.product_url, http_session)
            return {
                "product_id": str(product.id),
                "sku": product.sku,
                "html": html,
                "success": html is not None
            }
    
    def save_product_result(self, db: Session, product: MonitoredProduct, html: Optional[str]) -> bool:
        """Ürün sonucunu veritabanına kaydet (sequential - thread-safe)"""
        if not html:
            product.is_active = False
            product.last_fetched_at = datetime.utcnow()
            db.commit()
            logger.warning(f"No HTML for Trendyol SKU {product.sku} - marked as inactive")
            return False
        
        has_other_merchants = 'other-merchant' in html
        has_slider = 'slider__slide' in html
        has_price = 'price' in html.lower()
        
        logger.debug(f"SKU {product.sku}: HTML length={len(html)}, other-merchants={has_other_merchants}, slider={has_slider}, price={has_price}")
        
        
        sellers = self.parse_other_merchants(html)
        if not sellers:
            product.is_active = False
            product.last_fetched_at = datetime.utcnow()
            db.commit()
            logger.warning(f"No sellers found for Trendyol SKU {product.sku} (HTML={len(html)} bytes, other-merchants={has_other_merchants}) - marked as inactive")
            return False
        
        if not product.is_active:
            product.is_active = True
            logger.info(f"Trendyol SKU {product.sku} reactivated - sellers found")
        
        for seller in sellers:
            snapshot = SellerSnapshot(
                monitored_product_id=product.id,
                merchant_id=seller.get('merchant_id') or 'unknown',
                merchant_name=seller['merchant_name'],
                merchant_url_postfix=seller.get('merchant_url_postfix'),
                merchant_rating=seller.get('merchant_rating'),
                price=seller['price'],
                original_price=seller.get('original_price'),
                discount_rate=seller.get('discount_rate'),
                buybox_order=seller.get('buybox_order'),
                free_shipping=seller.get('free_shipping', False),
                fast_shipping=seller.get('fast_shipping', False),
                delivery_info=seller.get('delivery_info'),
                campaign_info=seller.get('campaign_info'),
                snapshot_date=datetime.utcnow()
            )
            db.add(snapshot)
        
        product.last_fetched_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Saved {len(sellers)} sellers for Trendyol SKU {product.sku}")
        return True
    
    async def fetch_all_products(self, db: Session, task: PriceMonitorTask, product_ids: List[str] = None, platform: str = "trendyol", fetch_type: str = "active"):
        """Tüm Trendyol izlenen ürünler için satıcı verilerini çek - 17 concurrent threads
        
        fetch_type:
        - active: Aktif ürünleri çek
        - last_inactive: Son fetch'te inactive olanları tekrar dene  
        - inactive: Tüm inactive ürünleri çek
        """
        query = db.query(MonitoredProduct).filter(
            MonitoredProduct.platform == 'trendyol'
        )
        
        if fetch_type == "active":
            query = query.filter(MonitoredProduct.is_active == True)
        elif fetch_type == "inactive":
            query = query.filter(MonitoredProduct.is_active == False)
        elif fetch_type == "last_inactive":
            last_task = db.query(PriceMonitorTask).filter(
                PriceMonitorTask.platform == 'trendyol',
                PriceMonitorTask.status == 'completed'
            ).order_by(PriceMonitorTask.completed_at.desc()).first()
            
            if last_task and last_task.last_inactive_skus:
                query = query.filter(MonitoredProduct.sku.in_(last_task.last_inactive_skus))
            else:
                query = query.filter(MonitoredProduct.is_active == False)
        
        if product_ids:
            query = query.filter(MonitoredProduct.id.in_(product_ids))
        
        products = query.all()
        
        task.total_products = len(products)
        task.status = "running"
        db.commit()
        
        if not products:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            db.commit()
            logger.info(f"No Trendyol products to fetch (fetch_type={fetch_type})")
            return
        
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=self.MAX_CONCURRENT_REQUESTS)
        
        completed = 0
        failed = 0
        failed_skus = []
        
        product_map = {str(p.id): p for p in products}
        sku_map = {str(p.id): p.sku for p in products}
        
        logger.info(f"Starting Trendyol fetch: {len(products)} products (fetch_type={fetch_type})")
        
        async with aiohttp.ClientSession(connector=connector) as http_session:
            tasks = [self.fetch_single_product(p, http_session) for p in products]
            
            for coro in asyncio.as_completed(tasks):
                db.refresh(task)
                if task.stop_requested:
                    logger.info(f"Stop requested, finishing after {completed} Trendyol products")
                    task.status = "stopped"
                    task.completed_at = datetime.utcnow()
                    db.commit()
                    return
                
                try:
                    result = await coro
                    product = product_map.get(result["product_id"])
                    sku = sku_map.get(result["product_id"], "unknown")
                    if product:
                        success = self.save_product_result(db, product, result["html"])
                        if success:
                            completed += 1
                        else:
                            failed += 1
                            failed_skus.append(sku)
                except Exception as e:
                    logger.error(f"Error processing Trendyol product: {e}")
                    failed += 1
                
                task.completed_products = completed
                task.failed_products = failed
                db.commit()
        
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.last_inactive_skus = failed_skus
        db.commit()
        
        logger.info(f"Trendyol fetch task completed: {completed} success, {failed} failed")


trendyol_price_monitor_service = TrendyolPriceMonitorService()
