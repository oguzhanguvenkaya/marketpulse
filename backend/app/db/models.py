import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, DateTime, Date, Float, Integer, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(20), nullable=False, index=True)
    external_id = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    seller_name = Column(String(255))
    category_path = Column(Text)
    image_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    snapshots = relationship("ProductSnapshot", back_populates="product", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True

class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    price = Column(Numeric(10, 2))
    rating = Column(Float)
    reviews_count = Column(Integer)
    in_stock = Column(Boolean, default=True)
    is_sponsored = Column(Boolean, default=False)
    snapshot_date = Column(Date, default=date.today, index=True)
    
    product = relationship("Product", back_populates="snapshots")
    
    class Config:
        from_attributes = True

class SearchTask(Base):
    __tablename__ = "search_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(255), nullable=False)
    platform = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")
    total_products = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    class Config:
        from_attributes = True
