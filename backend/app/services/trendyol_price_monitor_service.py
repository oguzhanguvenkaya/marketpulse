import os
import ssl
import random
import asyncio
import aiohttp
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.logger import price_monitor_logger as logger
from app.db.models import MonitoredProduct, SellerSnapshot, PriceMonitorTask


class TrendyolPriceMonitorService:
    """Trendyol ürün sayfasından JSON verisi ile satıcı bilgilerini çeken servis
    
    JSON verisi sayfa kaynağında SSR olarak embedded geliyor:
    window["__envoy_...__PROPS"] = { product: { merchantListing: { merchant, otherMerchants[] } } }
    
    Bu sayede render=true gerekmez, daha hızlı ve ucuz!
    """
    
    MAX_CONCURRENT_REQUESTS = 10  # Basic mode daha hızlı, concurrent limit artırıldı
    
    def __init__(self):
        self.api_key = os.environ.get('SCRAPPER_API', '')
        self._semaphore = None
        if not self.api_key:
            try:
                with open('/etc/secrets/SCRAPPER_API', 'r') as f:
                    self.api_key = f.read().strip()
            except:
                pass
    
    async def fetch_product_page(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """ScraperAPI ile Trendyol ürün sayfasını çek - BASIC MODE (JSON SSR'da mevcut)"""
        session_num = random.randint(1, 999999)
        proxy_url = 'http://proxy-server.scraperapi.com:8001'
        # render=true KALDIRILDI - JSON verisi basic modda mevcut
        proxy_user = f'scraperapi.session_number={session_num}'
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
                timeout=aiohttp.ClientTimeout(total=45)  # Basic mode daha hızlı
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    if 'merchantListing' in html:
                        logger.debug("Trendyol page fetched with merchantListing data")
                        return html
                    else:
                        logger.debug("Trendyol page fetched but no merchantListing found")
                        return html
                else:
                    logger.warning(f"Trendyol page error: status {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching Trendyol page: {e}")
            return None
    
    def parse_merchants_from_json(self, html: str) -> List[Dict[str, Any]]:
        """HTML içindeki JSON verisinden tüm satıcıları parse et (main + others)
        
        JSON yapısı:
        window["__envoy_...__PROPS"] = {
            product: {
                merchantListing: {
                    merchant: { ... },           // Ana satıcı (buybox winner)
                    winnerVariant: { price: {} }, // Ana satıcı fiyatı
                    promotions: [],               // Ana satıcı promosyonları
                    otherMerchants: [ ... ]       // Diğer satıcılar
                }
            }
        }
        """
        sellers = []
        
        # JSON verisini bul
        pattern = r'window\["__envoy[^"]*__PROPS"\]\s*=\s*(\{.*?\})(?:;|<)'
        matches = re.findall(pattern, html, re.DOTALL)
        
        merchant_listing = None
        for match in matches:
            try:
                data = json.loads(match)
                if 'product' in data and 'merchantListing' in data.get('product', {}):
                    merchant_listing = data['product']['merchantListing']
                    break
            except json.JSONDecodeError:
                continue
        
        if not merchant_listing:
            logger.debug("merchantListing not found in JSON")
            return sellers
        
        # 1. ANA SATICI (buybox winner) - buybox_order: 0
        main_merchant = merchant_listing.get('merchant', {})
        winner_variant = merchant_listing.get('winnerVariant', {})
        main_promotions = merchant_listing.get('promotions', [])
        
        if main_merchant and main_merchant.get('name'):
            price_info = winner_variant.get('price', {})
            discounted_price = price_info.get('discountedPrice', {}).get('value')
            selling_price = price_info.get('sellingPrice', {}).get('value')
            
            # Promosyon bilgilerini birleştir
            promo_names = [p.get('name', '') for p in main_promotions if p.get('name')]
            campaign_info = ' | '.join(promo_names) if promo_names else None
            
            # Kargo bedava kontrolü
            free_shipping = any('kargo bedava' in p.lower() for p in promo_names)
            
            main_seller = {
                'buybox_order': 0,  # Buybox winner
                'merchant_id': str(main_merchant.get('id', '')),
                'merchant_name': main_merchant.get('name'),
                'merchant_url_postfix': f"/sr?mid={main_merchant.get('id')}",
                'merchant_rating': main_merchant.get('sellerScore', {}).get('value'),
                'price': discounted_price,
                'original_price': selling_price if selling_price != discounted_price else None,
                'discount_rate': None,
                'free_shipping': free_shipping,
                'fast_shipping': False,
                'delivery_info': None,
                'campaign_info': campaign_info
            }
            
            # İndirim oranı hesapla
            if main_seller['price'] and main_seller['original_price']:
                main_seller['discount_rate'] = round(
                    (1 - main_seller['price'] / main_seller['original_price']) * 100, 1
                )
            
            sellers.append(main_seller)
            logger.debug(f"Main seller: {main_seller['merchant_name']} - {main_seller['price']} TL (buybox winner)")
        
        # 2. DİĞER SATICILAR - buybox_order: 1, 2, 3...
        other_merchants = merchant_listing.get('otherMerchants', [])
        
        for idx, other in enumerate(other_merchants):
            price_info = other.get('price', {})
            discounted_price = price_info.get('discountedPrice', {}).get('value')
            selling_price = price_info.get('sellingPrice', {}).get('value')
            
            # Promosyon bilgileri
            promos = other.get('promotions', [])
            promo_names = [p.get('name', '') for p in promos if p.get('name')]
            campaign_info = ' | '.join(promo_names) if promo_names else None
            free_shipping = any('kargo bedava' in p.lower() for p in promo_names)
            
            other_seller = {
                'buybox_order': idx + 1,
                'merchant_id': str(other.get('id', '')),
                'merchant_name': other.get('name'),
                'merchant_url_postfix': f"/sr?mid={other.get('id')}",
                'merchant_rating': other.get('sellerScore', {}).get('value'),
                'price': discounted_price,
                'original_price': selling_price if selling_price != discounted_price else None,
                'discount_rate': None,
                'free_shipping': free_shipping,
                'fast_shipping': False,
                'delivery_info': None,
                'campaign_info': campaign_info
            }
            
            # İndirim oranı hesapla
            if other_seller['price'] and other_seller['original_price']:
                other_seller['discount_rate'] = round(
                    (1 - other_seller['price'] / other_seller['original_price']) * 100, 1
                )
            
            if other_seller['merchant_name']:
                sellers.append(other_seller)
                logger.debug(f"Other seller [{idx+1}]: {other_seller['merchant_name']} - {other_seller['price']} TL")
        
        logger.info(f"Parsed {len(sellers)} total sellers (1 main + {len(other_merchants)} others)")
        return sellers
    
    async def fetch_single_product(self, product_id: str, sku: str, product_url: str, http_session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Tek bir ürün için HTTP isteği yap ve sonucu döndür (thread-safe)"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        async with self._semaphore:
            html = await self.fetch_product_page(product_url, http_session)
            return {
                "product_id": product_id,
                "sku": sku,
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
        
        has_merchant_listing = 'merchantListing' in html
        
        logger.debug(f"SKU {product.sku}: HTML length={len(html)}, merchantListing={has_merchant_listing}")
        
        # JSON parsing ile tüm satıcıları al (main + others)
        sellers = self.parse_merchants_from_json(html)
        if not sellers:
            product.is_active = False
            product.last_fetched_at = datetime.utcnow()
            db.commit()
            logger.warning(f"No sellers found for Trendyol SKU {product.sku} (HTML={len(html)} bytes, merchantListing={has_merchant_listing}) - marked as inactive")
            return False
        
        valid_sellers = [s for s in sellers if s.get('price') is not None]
        
        if not valid_sellers:
            product.is_active = False
            product.last_fetched_at = datetime.utcnow()
            db.commit()
            logger.warning(f"No valid sellers (with price) for Trendyol SKU {product.sku} - marked as inactive")
            return False
        
        if not product.is_active:
            product.is_active = True
            logger.info(f"Trendyol SKU {product.sku} reactivated - sellers found")
        
        for seller in valid_sellers:
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
        
        logger.info(f"Saved {len(valid_sellers)} sellers for Trendyol SKU {product.sku}")
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
            tasks = [
                self.fetch_single_product(str(p.id), p.sku, p.product_url, http_session) 
                for p in products
            ]
            
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
                    db.rollback()
                    failed += 1
                
                try:
                    task.completed_products = completed
                    task.failed_products = failed
                    db.commit()
                except Exception as e:
                    logger.error(f"Error updating task progress: {e}")
                    db.rollback()
        
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.last_inactive_skus = failed_skus
        db.commit()
        
        logger.info(f"Trendyol fetch task completed: {completed} success, {failed} failed")


trendyol_price_monitor_service = TrendyolPriceMonitorService()
