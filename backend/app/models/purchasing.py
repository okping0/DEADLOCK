from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    order_date = Column(DateTime(timezone=True), server_default=func.now())
    expected_date = Column(DateTime(timezone=True), nullable=True)
    received_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="PENDING")  # PENDING, ORDERED, RECEIVED, CANCELLED
    total_amount = Column(Float, default=0.0)
    # True if this PO was created by the system's reorder recommendation, not a human
    auto_generated = Column(String, default="MANUAL")  # MANUAL, AUTO_SUGGESTED

    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")
    items = relationship("PurchaseOrderItem", back_populates="po", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)
    unit_cost = Column(Float, nullable=False)

    po = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")
