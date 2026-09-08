from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ---------- Customer ----------
class CustomerBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerOut(CustomerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Sales Order ----------
class SalesOrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class SalesOrderCreate(BaseModel):
    customer_id: int
    warehouse_id: int
    items: List[SalesOrderItemCreate]


class SalesOrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True


class SalesOrderOut(BaseModel):
    id: int
    customer_id: int
    warehouse_id: int
    order_date: datetime
    status: str
    total_amount: float
    items: List[SalesOrderItemOut]

    class Config:
        from_attributes = True
