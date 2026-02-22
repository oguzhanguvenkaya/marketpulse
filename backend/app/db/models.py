import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, DateTime, Date, Float, Integer, Boolean, ForeignKey, Numeric, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(20), nullable=False, index=True)
    external_id = Column(Text, nullable=False)
    sku = Column(String(100))
    barcode = Column(String(50))
    name = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    brand = Column(String(255))
    seller_name = Column(String(255))
    seller_rating = Column(Float)
    category_path = Column(Text)
    category_hierarchy = Column(Text)
    image_url = Column(Text)
    description = Column(Text)
    origin_country = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    snapshots = relationship("ProductSnapshot", back_populates="product", cascade="all, delete-orphan")
    other_sellers = relationship("ProductSeller", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True

class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    price = Column(Numeric(10, 2))
    discounted_price = Column(Numeric(10, 2))
    discount_percentage = Column(Float)
    rating = Column(Float)
    reviews_count = Column(Integer)
    stock_count = Column(Integer)
    in_stock = Column(Boolean, default=True)
    is_sponsored = Column(Boolean, default=False)
    coupons = Column(JSON)
    campaigns = Column(JSON)
    snapshot_date = Column(Date, default=date.today, index=True)
    
    product = relationship("Product", back_populates="snapshots")
    
    class Config:
        from_attributes = True

class ProductSeller(Base):
    __tablename__ = "product_sellers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    seller_name = Column(String(255), nullable=False)
    seller_rating = Column(Float)
    price = Column(Numeric(10, 2))
    is_authorized = Column(Boolean, default=False)
    shipping_info = Column(String(255))
    snapshot_date = Column(Date, default=date.today)
    
    product = relationship("Product", back_populates="other_sellers")
    
    class Config:
        from_attributes = True

class ProductReview(Base):
    __tablename__ = "product_reviews"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    author = Column(String(255))
    rating = Column(Integer)
    review_text = Column(Text)
    review_date = Column(Date)
    seller_name = Column(String(255))
    is_helpful_count = Column(Integer, default=0)
    
    product = relationship("Product", back_populates="reviews")
    
    class Config:
        from_attributes = True

class SearchTask(Base):
    __tablename__ = "search_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(255), nullable=False)
    platform = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")
    total_products = Column(Integer, default=0)
    total_sponsored_products = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    sponsored_brands = relationship("SponsoredBrandAd", back_populates="search_task", cascade="all, delete-orphan")
    sponsored_products = relationship("SearchSponsoredProduct", back_populates="search_task", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True


class SponsoredBrandAd(Base):
    """Marka reklamları - arama sayfasındaki carousel reklamlar (AUTO POWER, MTS Kimya vb.)"""
    __tablename__ = "sponsored_brand_ads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_task_id = Column(UUID(as_uuid=True), ForeignKey("search_tasks.id"), nullable=False, index=True)
    seller_name = Column(String(255), nullable=False)
    seller_id = Column(String(100))
    position = Column(Integer)
    products = Column(JSON)
    snapshot_date = Column(Date, default=date.today)
    
    search_task = relationship("SearchTask", back_populates="sponsored_brands")
    
    class Config:
        from_attributes = True


class SearchSponsoredProduct(Base):
    """Sponsorlu ürünler - arama sonuçlarında 'Reklam' badge'i olan ürünler (sıralı liste)"""
    __tablename__ = "search_sponsored_products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_task_id = Column(UUID(as_uuid=True), ForeignKey("search_tasks.id"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False)
    product_url = Column(Text, nullable=False)
    product_name = Column(Text)
    seller_name = Column(String(255))
    price = Column(Numeric(10, 2))
    discounted_price = Column(Numeric(10, 2))
    image_url = Column(Text)
    payload = Column(JSON)
    snapshot_date = Column(Date, default=date.today)
    
    search_task = relationship("SearchTask", back_populates="sponsored_products")
    
    class Config:
        from_attributes = True


class MonitoredProduct(Base):
    """İzlenen ürünler - distribütör olarak takip edilen SKU'lar"""
    __tablename__ = "monitored_products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(20), nullable=False, default='hepsiburada', index=True)  # hepsiburada, trendyol
    sku = Column(String(100), nullable=False, index=True)  # unique kaldırıldı - platform ile birlikte unique olacak
    barcode = Column(String(50))  # Trendyol için barkod
    product_url = Column(Text, nullable=False)
    product_name = Column(Text)
    brand = Column(String(255), index=True)
    seller_stock_code = Column(String(100), index=True)  # Satıcı stok kodu
    threshold_price = Column(Numeric(10, 2))  # Eşik fiyat - original_price üzerinden alert (satıcı indirimine izin verir)
    alert_campaign_price = Column(Numeric(10, 2))  # Campaign price eşik - Campaign API'den gelen indirimli fiyat için alert
    image_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_fetched_at = Column(DateTime)
    
    seller_snapshots = relationship("SellerSnapshot", back_populates="monitored_product", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_monitored_products_platform_active', 'platform', 'is_active'),
    )

    class Config:
        from_attributes = True


class SellerSnapshot(Base):
    """Satıcı anlık fiyat verisi - her fetch'te güncellenir"""
    __tablename__ = "seller_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    monitored_product_id = Column(UUID(as_uuid=True), ForeignKey("monitored_products.id"), nullable=False, index=True)
    merchant_id = Column(String(100), nullable=False)
    merchant_name = Column(String(255), nullable=False)
    merchant_logo = Column(Text)
    merchant_url_postfix = Column(String(255))
    merchant_rating = Column(Float)
    merchant_rating_count = Column(Integer)
    merchant_city = Column(String(100))
    price = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2))
    minimum_price = Column(Numeric(10, 2))
    discount_rate = Column(Float)
    stock_quantity = Column(Integer)
    buybox_order = Column(Integer)
    free_shipping = Column(Boolean, default=False)
    fast_shipping = Column(Boolean, default=False)
    is_fulfilled_by_hb = Column(Boolean, default=False)
    delivery_info = Column(Text)  # Trendyol: teslimat bilgisi
    campaign_info = Column(Text)  # Trendyol: kampanya bilgisi (Sepette %5 indirim vb.)
    campaigns = Column(JSON)  # Hepsiburada: kampanya ve indirim tag'leri (tagList'ten filtrelenen)
    campaign_price = Column(Numeric(10, 2))  # Sepete özel/kampanyalı fiyat (satıcı sayfasından kazınmış)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    
    monitored_product = relationship("MonitoredProduct", back_populates="seller_snapshots")

    __table_args__ = (
        Index('ix_seller_snapshots_product_merchant_date',
              'monitored_product_id', 'merchant_id', 'snapshot_date'),
    )

    class Config:
        from_attributes = True


class PriceMonitorTask(Base):
    """Fiyat izleme görevi - toplu SKU çekme işlemi"""
    __tablename__ = "price_monitor_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(50), default="hepsiburada")
    status = Column(String(20), default="pending")
    stop_requested = Column(Boolean, default=False)
    total_products = Column(Integer, default=0)
    completed_products = Column(Integer, default=0)
    failed_products = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Yeni alanlar: Session bazlı inactive takibi ve resume desteği
    last_inactive_skus = Column(JSON, default=list)  # Bu fetch'te inactive olan SKU'lar
    last_processed_index = Column(Integer, default=0)  # Resume için son işlenen index
    fetch_type = Column(String(20), default="active")  # active, last_inactive, inactive
    
    class Config:
        from_attributes = True


class JsonFile(Base):
    __tablename__ = "json_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    json_content = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class Config:
        from_attributes = True


class ScrapeJob(Base):
    """URL kazıma görevi"""
    __tablename__ = "scrape_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default="pending")
    total_urls = Column(Integer, default=0)
    completed_urls = Column(Integer, default=0)
    failed_urls = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    scrape_results = relationship("ScrapeResult", back_populates="scrape_job", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True


class ScrapeResult(Base):
    """Kazınan URL sonucu"""
    __tablename__ = "scrape_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scrape_job_id = Column(UUID(as_uuid=True), ForeignKey("scrape_jobs.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    product_name = Column(Text)
    barcode = Column(Text)
    status = Column(String(20), default="pending")
    scraped_data = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    scrape_job = relationship("ScrapeJob", back_populates="scrape_results")
    
    class Config:
        from_attributes = True


class TranscriptJob(Base):
    __tablename__ = "transcript_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default="pending")
    total_videos = Column(Integer, default=0)
    completed_videos = Column(Integer, default=0)
    failed_videos = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    transcript_results = relationship("TranscriptResult", back_populates="transcript_job", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True


class TranscriptResult(Base):
    __tablename__ = "transcript_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_job_id = Column(UUID(as_uuid=True), ForeignKey("transcript_jobs.id"), nullable=False, index=True)
    video_url = Column(Text, nullable=False)
    product_name = Column(Text)
    barcode = Column(Text)
    status = Column(String(20), default="pending")
    language = Column(String(50))
    language_code = Column(String(10))
    is_generated = Column(Boolean)
    transcript_text = Column(Text)
    transcript_snippets = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transcript_job = relationship("TranscriptJob", back_populates="transcript_results")
    
    class Config:
        from_attributes = True


class StoreProduct(Base):
    __tablename__ = "store_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(30), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    sku = Column(String(100), index=True)
    barcode = Column(String(50), index=True)
    product_name = Column(Text)
    brand = Column(String(255), index=True)
    category = Column(Text)
    category_breadcrumbs = Column(JSON)
    price = Column(Numeric(10, 2))
    currency = Column(String(10))
    availability = Column(String(100))
    rating = Column(Float)
    rating_count = Column(Integer)
    review_count = Column(Integer)
    reviews = Column(JSON)
    image_url = Column(Text)
    images = Column(JSON)
    description = Column(Text)
    seller_name = Column(String(255))
    shipping_info = Column(JSON)
    return_policy = Column(JSON)
    product_specs = Column(JSON)
    additional_properties = Column(JSON)
    related_products = Column(JSON)
    og_data = Column(JSON)
    scrape_result_id = Column(Integer, index=True)
    monitored_product_id = Column(UUID(as_uuid=True), index=True)
    raw_scraped_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_store_products_platform_brand', 'platform', 'brand'),
        Index('ix_store_products_platform_sku', 'platform', 'sku'),
    )

    class Config:
        from_attributes = True


class CategorySession(Base):
    __tablename__ = "category_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(30), nullable=False, index=True)
    category_url = Column(Text, nullable=False)
    category_name = Column(Text)
    breadcrumbs = Column(JSON)
    total_products = Column(Integer, default=0)
    pages_scraped = Column(Integer, default=0)
    filter_data = Column(JSON, nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category_products = relationship("CategoryProduct", back_populates="session", cascade="all, delete-orphan")

    class Config:
        from_attributes = True


class CategoryProduct(Base):
    __tablename__ = "category_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("category_sessions.id"), nullable=False, index=True)
    name = Column(Text)
    url = Column(Text)
    image_url = Column(Text)
    brand = Column(String(255))
    price = Column(Numeric(10, 2))
    original_price = Column(Numeric(10, 2))
    discount_percentage = Column(Float)
    rating = Column(Float)
    review_count = Column(Integer)
    is_sponsored = Column(Boolean, default=False)
    campaign_text = Column(Text)
    seller_name = Column(String(255))
    page_number = Column(Integer, default=1)
    position = Column(Integer)
    detail_fetched = Column(Boolean, default=False)
    detail_data = Column(JSON)
    sku = Column(String(100))
    barcode = Column(String(50))
    description = Column(Text)
    specs = Column(JSON)
    shipping_type = Column(String(100))
    stock_status = Column(String(50))
    category_path = Column(Text)
    seller_list = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CategorySession", back_populates="category_products")

    __table_args__ = (
        Index('ix_category_products_session_page', 'session_id', 'page_number'),
    )

    class Config:
        from_attributes = True
