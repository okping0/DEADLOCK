from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sales import SalesOrder, SalesOrderItem
from app.models.inventory import Product, Stock, StockMovement
from app.schemas.sales import SalesOrderCreate, SalesOrderOut

router = APIRouter(prefix="/sales-orders", tags=["Sales Orders"], dependencies=[Depends(get_current_user)])


@router.post("/", response_model=SalesOrderOut)
def create_sales_order(order_in: SalesOrderCreate, db: Session = Depends(get_db)):
    """
    Creates a sales order, deducts stock for each line item, and snapshots the
    unit price at time of sale (so historical orders stay accurate even if
    product prices change later).
    Stock is checked for ALL items before any deduction happens — an order
    should not partially succeed.
    """
    # Step 1: validate everything before touching stock
    line_data = []
    for item in order_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        stock = db.query(Stock).filter(
            Stock.product_id == item.product_id,
            Stock.warehouse_id == order_in.warehouse_id,
        ).first()
        available = stock.quantity if stock else 0
        if available < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{product.name}': have {available}, need {item.quantity}",
            )
        line_data.append((product, stock, item.quantity))

    # Step 2: create the order
    order = SalesOrder(customer_id=order_in.customer_id, warehouse_id=order_in.warehouse_id, status="FULFILLED")
    db.add(order)
    db.flush()  # get order.id before committing

    total = 0.0
    for product, stock, qty in line_data:
        order_item = SalesOrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=qty,
            unit_price=product.unit_price,  # snapshot price at sale time
        )
        db.add(order_item)
        total += product.unit_price * qty

        # Step 3: deduct stock + log movement
        stock.quantity -= qty
        db.add(StockMovement(
            product_id=product.id,
            warehouse_id=order_in.warehouse_id,
            movement_type="OUT",
            quantity=-qty,
            reference=f"sales_order:{order.id}",
        ))

    order.total_amount = total
    db.commit()
    db.refresh(order)
    return order


@router.get("/", response_model=List[SalesOrderOut])
def list_sales_orders(
    customer_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(SalesOrder)
    if customer_id is not None:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if warehouse_id is not None:
        query = query.filter(SalesOrder.warehouse_id == warehouse_id)
    return query.order_by(SalesOrder.order_date.desc()).all()


@router.get("/{order_id}", response_model=SalesOrderOut)
def get_sales_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return order
