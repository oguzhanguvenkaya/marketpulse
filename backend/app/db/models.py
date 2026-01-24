import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, DateTime, Date, Float, Integer, Boolean, ForeignKey, Numeric, JSON
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
    sku = Column(String(100), nullable=False, unique=True, index=True)
    product_url = Column(Text, nullable=False)
    product_name = Column(Text)
    brand = Column(String(255))
    image_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_fetched_at = Column(DateTime)
    
    seller_snapshots = relationship("SellerSnapshot", back_populates="monitored_product", cascade="all, delete-orphan")
    
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
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    
    monitored_product = relationship("MonitoredProduct", back_populates="seller_snapshots")
    
    class Config:
        from_attributes = True


class PriceMonitorTask(Base):
    """Fiyat izleme görevi - toplu SKU çekme işlemi"""
    __tablename__ = "price_monitor_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default="pending")
    total_products = Column(Integer, default=0)
    completed_products = Column(Integer, default=0)
    failed_products = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    class Config:
        from_attributes = True
