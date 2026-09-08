from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity_ordered: int
    unit_cost: float


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    expected_date: Optional[datetime] = None
    items: List[PurchaseOrderItemCreate]


class PurchaseOrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity_ordered: int
    quantity_received: int
    unit_cost: float

    class Config:
        from_attributes = True


class PurchaseOrderOut(BaseModel):
    id: int
    supplier_id: int
    warehouse_id: int
    order_date: datetime
    expected_date: Optional[datetime]
    received_date: Optional[datetime]
    status: str
    total_amount: float
    items: List[PurchaseOrderItemOut]

    class Config:
        from_attributes = True


class ReceiveItem(BaseModel):
    product_id: int
    quantity_received: int


class ReceivePO(BaseModel):
    items: List[ReceiveItem]
