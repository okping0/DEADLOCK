from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    products = relationship("Product", back_populates="category")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    avg_lead_time_days = Column(Integer, default=7)  # used in reorder calc
    reliability_score = Column(Float, default=1.0)   # 0-1, based on on-time delivery history

    products = relationship("ProductSupplier", back_populates="supplier")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)

    stock_entries = relationship("Stock", back_populates="warehouse")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    unit_price = Column(Float, nullable=False, default=0.0)
    unit_cost = Column(Float, nullable=False, default=0.0)
    reorder_point = Column(Integer, default=10)       # manual override, else ML computes
    safety_stock = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    category = relationship("Category", back_populates="products")
    stock_entries = relationship("Stock", back_populates="product")
    suppliers = relationship("ProductSupplier", back_populates="product")


class ProductSupplier(Base):
    """Many-to-many: a product can have multiple suppliers, each with its own price/lead time."""
    __tablename__ = "product_suppliers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    supplier_price = Column(Float, nullable=False)
    lead_time_days = Column(Integer, default=7)
    is_preferred = Column(Boolean, default=False)

    product = relationship("Product", back_populates="suppliers")
    supplier = relationship("Supplier", back_populates="products")


class Stock(Base):
    """Current stock level of a product at a specific warehouse."""
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    product = relationship("Product", back_populates="stock_entries")
    warehouse = relationship("Warehouse", back_populates="stock_entries")


class StockMovement(Base):
    """Audit log of every stock change — inbound, outbound, transfer, adjustment."""
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    movement_type = Column(String, nullable=False)  # IN, OUT, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT
    quantity = Column(Integer, nullable=False)
    reference = Column(String, nullable=True)  # e.g. order id, PO id, transfer id
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product")
    warehouse = relationship("Warehouse")


class Transfer(Base):
    """Stock transfer between two warehouses."""
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, IN_TRANSIT, COMPLETED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    product = relationship("Product")
