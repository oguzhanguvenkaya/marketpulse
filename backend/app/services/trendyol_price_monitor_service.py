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
from app.db.models import MonitoredProduct, SellerSnapshot, PriceMonitorTask


class TrendyolPriceMonitorService:
    """Trendyol ürün sayfasından other-merchants bölümündeki satıcı verilerini çeken servis"""
    
    def __init__(self):
        self.api_key = os.environ.get('SCRAPPER_API', '')
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
    
    async def fetch_product_page(self, url: str) -> Optional[str]:
        """ScraperAPI ile Trendyol ürün sayfasını çek - proxy port ile render"""
        session_num = random.randint(1, 999999)
        proxy_url = 'http://proxy-server.scraperapi.com:8001'
        proxy_user = f'scraperapi.render=true.country_code=tr.device_type=desktop.premium=true.session_number={session_num}'
        proxy_pass = self.api_key
        
        proxy_auth = aiohttp.BasicAuth(proxy_user, proxy_pass)
        
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.trendyol.com/'
        }
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, 
                    proxy=proxy_url, 
                    proxy_auth=proxy_auth, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        if 'other-merchant' in html or 'slider__slide' in html:
                            print(f"Trendyol page fetched successfully with proxy port")
                            return html
                        else:
                            print(f"Trendyol page fetched but no other-merchants section found")
                            debug_path = f"/tmp/scraping_debug/trendyol_{random.randint(1000,9999)}.html"
                            import os
                            os.makedirs('/tmp/scraping_debug', exist_ok=True)
                            with open(debug_path, 'w', encoding='utf-8') as f:
                                f.write(html[:100000])
                            print(f"Debug HTML saved to {debug_path}")
                            return html
                    else:
                        print(f"Trendyol page error: status {resp.status}")
                        return None
        except Exception as e:
            print(f"Error fetching Trendyol page: {e}")
            return None
    
    def parse_other_merchants(self, html: str) -> List[Dict[str, Any]]:
        """HTML'den other-merchants bölümündeki satıcı bilgilerini parse et"""
        sellers = []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        other_merchants = soup.find(id='other-merchants')
        if not other_merchants:
            print("other-merchants bölümü bulunamadı")
            return sellers
        
        slides = other_merchants.find_all('div', {'data-testid': 'slide'})
        
        for idx, slide in enumerate(slides):
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
            
            name_elem = slide.find('div', class_='merchant-header-name')
            if name_elem:
                seller['merchant_name'] = name_elem.get_text(strip=True)
                parent_a = name_elem.find_parent('a')
                if parent_a and parent_a.get('href'):
                    seller['merchant_id'] = self._extract_merchant_id(parent_a['href'])
                    seller['merchant_url_postfix'] = parent_a['href']
            
            score_elem = slide.find('div', {'data-testid': 'seller-score'})
            if score_elem:
                try:
                    seller['merchant_rating'] = float(score_elem.get_text(strip=True).replace(',', '.'))
                except:
                    pass
            
            new_price_elem = slide.find('p', class_='new-price')
            if new_price_elem:
                seller['price'] = self._parse_price(new_price_elem.get_text(strip=True))
            
            old_price_elem = slide.find('p', class_='old-price')
            if old_price_elem:
                seller['original_price'] = self._parse_price(old_price_elem.get_text(strip=True))
            
            if not seller['price']:
                current_price_elem = slide.find('div', class_='price-current-price')
                if current_price_elem:
                    seller['price'] = self._parse_price(current_price_elem.get_text(strip=True))
            
            if seller['price'] and seller['original_price']:
                seller['discount_rate'] = round((1 - seller['price'] / seller['original_price']) * 100, 1)
            
            free_cargo = slide.find('div', {'data-testid': 'free-cargo-promotion'})
            if free_cargo:
                seller['free_shipping'] = True
            
            fast_delivery = slide.find('div', {'data-testid': 'tomorrow-shipping-delivery'})
            if fast_delivery:
                seller['fast_shipping'] = True
            
            delivery_elem = slide.find('div', class_='other-merchant-delivery-container')
            if delivery_elem:
                seller['delivery_info'] = delivery_elem.get_text(strip=True)
            
            campaign_info_elem = slide.find('p', class_='info-text')
            if campaign_info_elem:
                seller['campaign_info'] = campaign_info_elem.get_text(strip=True)
            
            if seller['merchant_name']:
                sellers.append(seller)
        
        return sellers
    
    async def fetch_and_save_product(self, db: Session, product: MonitoredProduct) -> bool:
        """Tek bir ürün için satıcı verilerini çek ve kaydet"""
        html = await self.fetch_product_page(product.product_url)
        if not html:
            return False
        
        sellers = self.parse_other_merchants(html)
        if not sellers:
            print(f"No sellers found for {product.sku}")
            return False
        
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
        
        print(f"Saved {len(sellers)} sellers for Trendyol SKU {product.sku}")
        return True
    
    async def fetch_all_products(self, db: Session, task: PriceMonitorTask, product_ids: List[str] = None):
        """Tüm Trendyol izlenen ürünler için satıcı verilerini çek"""
        query = db.query(MonitoredProduct).filter(
            MonitoredProduct.platform == 'trendyol',
            MonitoredProduct.is_active == True
        )
        
        if product_ids:
            query = query.filter(MonitoredProduct.id.in_(product_ids))
        
        products = query.all()
        
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
                print(f"Error processing Trendyol product {product.sku}: {e}")
                failed += 1
            
            task.completed_products = completed
            task.failed_products = failed
            db.commit()
            
            await asyncio.sleep(2)
        
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        
        print(f"Trendyol fetch task completed: {completed} success, {failed} failed")


trendyol_price_monitor_service = TrendyolPriceMonitorService()
