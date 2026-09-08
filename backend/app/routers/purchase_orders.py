from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.purchasing import PurchaseOrder, PurchaseOrderItem
from app.models.inventory import Stock, StockMovement
from app.schemas.purchasing import PurchaseOrderCreate, PurchaseOrderOut, ReceivePO

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"], dependencies=[Depends(get_current_user)])


@router.post("/", response_model=PurchaseOrderOut)
def create_purchase_order(po_in: PurchaseOrderCreate, db: Session = Depends(get_db)):
    """Creates a PO in ORDERED status. Stock is NOT added yet — that happens on receiving."""
    po = PurchaseOrder(
        supplier_id=po_in.supplier_id,
        warehouse_id=po_in.warehouse_id,
        expected_date=po_in.expected_date,
        status="ORDERED",
    )
    db.add(po)
    db.flush()

    total = 0.0
    for item in po_in.items:
        db.add(PurchaseOrderItem(
            po_id=po.id,
            product_id=item.product_id,
            quantity_ordered=item.quantity_ordered,
            unit_cost=item.unit_cost,
        ))
        total += item.quantity_ordered * item.unit_cost

    po.total_amount = total
    db.commit()
    db.refresh(po)
    return po


@router.get("/", response_model=List[PurchaseOrderOut])
def list_purchase_orders(
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseOrder)
    if supplier_id is not None:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    if status is not None:
        query = query.filter(PurchaseOrder.status == status)
    return query.order_by(PurchaseOrder.order_date.desc()).all()


@router.get("/{po_id}", response_model=PurchaseOrderOut)
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.post("/{po_id}/receive", response_model=PurchaseOrderOut)
def receive_purchase_order(po_id: int, receive_in: ReceivePO, db: Session = Depends(get_db)):
    """
    Marks items as received, adds the received quantity to stock, and logs
    the movement. Supports partial receiving — PO moves to RECEIVED only once
    every line item is fully received, otherwise stays ORDERED.
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status == "RECEIVED":
        raise HTTPException(status_code=400, detail="Purchase order already fully received")

    items_by_product = {item.product_id: item for item in po.items}

    for r in receive_in.items:
        po_item = items_by_product.get(r.product_id)
        if not po_item:
            raise HTTPException(status_code=400, detail=f"Product {r.product_id} not part of this PO")

        remaining = po_item.quantity_ordered - po_item.quantity_received
        if r.quantity_received > remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot receive {r.quantity_received} for product {r.product_id}; only {remaining} remaining",
            )

        po_item.quantity_received += r.quantity_received

        stock = db.query(Stock).filter(
            Stock.product_id == r.product_id, Stock.warehouse_id == po.warehouse_id
        ).first()
        if not stock:
            stock = Stock(product_id=r.product_id, warehouse_id=po.warehouse_id, quantity=0)
            db.add(stock)
            db.flush()
        stock.quantity += r.quantity_received

        db.add(StockMovement(
            product_id=r.product_id,
            warehouse_id=po.warehouse_id,
            movement_type="IN",
            quantity=r.quantity_received,
            reference=f"purchase_order:{po.id}",
        ))

    # check if fully received across all line items
    db.flush()
    fully_received = all(item.quantity_received >= item.quantity_ordered for item in po.items)
    if fully_received:
        po.status = "RECEIVED"
        po.received_date = datetime.now(timezone.utc)

    db.commit()
    db.refresh(po)
    return po
