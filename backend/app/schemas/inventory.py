from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------- Category ----------
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Supplier ----------
class SupplierBase(BaseModel):
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    avg_lead_time_days: int = 7
    reliability_score: float = 1.0


class SupplierCreate(SupplierBase):
    pass


class SupplierOut(SupplierBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Warehouse ----------
class WarehouseBase(BaseModel):
    name: str
    location: Optional[str] = None
    capacity: Optional[int] = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseOut(WarehouseBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Product ----------
class ProductBase(BaseModel):
    sku: str
    name: str
    category_id: Optional[int] = None
    unit_price: float
    unit_cost: float
    reorder_point: int = 10
    safety_stock: int = 5
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    unit_price: Optional[float] = None
    unit_cost: Optional[float] = None
    reorder_point: Optional[int] = None
    safety_stock: Optional[int] = None
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Stock ----------
class StockOut(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    quantity: int

    class Config:
        from_attributes = True


class StockAdjust(BaseModel):
    product_id: int
    warehouse_id: int
    quantity_change: int  # positive = add, negative = remove
    reason: str  # movement_type: IN, OUT, ADJUSTMENT


# ---------- Transfer ----------
class TransferCreate(BaseModel):
    product_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: int


class TransferOut(BaseModel):
    id: int
    product_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
