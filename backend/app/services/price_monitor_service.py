import os
import ssl
import random
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
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
    
    async def fetch_listings(self, sku: str) -> Optional[Dict[str, Any]]:
        """Tek bir SKU için listings API'sinden satıcı verilerini çek - ScraperAPI HTTP API"""
        import urllib.parse
        
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
                        print(f"Listings API error for {sku}: status {resp.status}")
                        return None
        except Exception as e:
            print(f"Error fetching listings for {sku}: {e}")
            return None
    
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
            
            sellers.append(seller)
        
        return sellers
    
    async def fetch_and_save_product(self, db: Session, product: MonitoredProduct) -> bool:
        """Tek bir ürün için satıcı verilerini çek ve kaydet"""
        sku = product.sku
        if sku.startswith('SKU: '):
            sku = sku.replace('SKU: ', '')
        
        data = await self.fetch_listings(sku)
        if not data:
            return False
        
        sellers = self.parse_listings(data)
        if not sellers:
            return False
        
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
                snapshot_date=datetime.utcnow()
            )
            db.add(snapshot)
        
        product.last_fetched_at = datetime.utcnow()
        db.commit()
        
        print(f"Saved {len(sellers)} sellers for SKU {sku}")
        return True
    
    async def fetch_all_products(self, db: Session, task: PriceMonitorTask, product_ids: List[str] = None):
        """Tüm izlenen ürünler için satıcı verilerini çek"""
        if product_ids:
            products = db.query(MonitoredProduct).filter(
                MonitoredProduct.id.in_(product_ids),
                MonitoredProduct.is_active == True
            ).all()
        else:
            products = db.query(MonitoredProduct).filter(
                MonitoredProduct.is_active == True
            ).all()
        
        task.total_products = len(products)
        task.status = "running"
        db.commit()
        
        completed = 0
        failed = 0
        
        for product in products:
            try:
                success = await self.fetch_and_save_product(db, product)
                if success:
                    completed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error processing product {product.sku}: {e}")
                failed += 1
            
            task.completed_products = completed
            task.failed_products = failed
            db.commit()
            
            await asyncio.sleep(1)
        
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        
        print(f"Fetch task completed: {completed} success, {failed} failed")


price_monitor_service = PriceMonitorService()
