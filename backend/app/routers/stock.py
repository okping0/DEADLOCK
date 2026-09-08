from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.inventory import Stock, StockMovement, Transfer
from app.schemas.inventory import StockOut, StockAdjust, TransferCreate, TransferOut

router = APIRouter(prefix="/stock", tags=["Stock"], dependencies=[Depends(get_current_user)])


def _get_or_create_stock(db: Session, product_id: int, warehouse_id: int) -> Stock:
    stock = db.query(Stock).filter(
        Stock.product_id == product_id, Stock.warehouse_id == warehouse_id
    ).first()
    if not stock:
        stock = Stock(product_id=product_id, warehouse_id=warehouse_id, quantity=0)
        db.add(stock)
        db.flush()  # get an id without committing yet
    return stock


@router.get("/", response_model=List[StockOut])
def list_stock(
    warehouse_id: Optional[int] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Stock)
    if warehouse_id is not None:
        query = query.filter(Stock.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.filter(Stock.product_id == product_id)
    return query.all()


@router.post("/adjust", response_model=StockOut)
def adjust_stock(adj: StockAdjust, db: Session = Depends(get_db)):
    """
    Single entry point for ALL stock changes — sales, purchases, manual corrections.
    Every adjustment writes a StockMovement row too, so we always have history for forecasting.
    """
    stock = _get_or_create_stock(db, adj.product_id, adj.warehouse_id)

    new_quantity = stock.quantity + adj.quantity_change
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock for this adjustment")

    stock.quantity = new_quantity

    movement = StockMovement(
        product_id=adj.product_id,
        warehouse_id=adj.warehouse_id,
        movement_type=adj.reason,
        quantity=adj.quantity_change,
    )
    db.add(movement)
    db.commit()
    db.refresh(stock)
    return stock


@router.post("/transfer", response_model=TransferOut)
def create_transfer(transfer_in: TransferCreate, db: Session = Depends(get_db)):
    """Move stock between warehouses. Executes immediately (no separate approval step for MVP)."""
    if transfer_in.from_warehouse_id == transfer_in.to_warehouse_id:
        raise HTTPException(status_code=400, detail="Source and destination warehouses must differ")

    from_stock = _get_or_create_stock(db, transfer_in.product_id, transfer_in.from_warehouse_id)
    if from_stock.quantity < transfer_in.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock at source warehouse")

    to_stock = _get_or_create_stock(db, transfer_in.product_id, transfer_in.to_warehouse_id)

    from_stock.quantity -= transfer_in.quantity
    to_stock.quantity += transfer_in.quantity

    transfer = Transfer(
        product_id=transfer_in.product_id,
        from_warehouse_id=transfer_in.from_warehouse_id,
        to_warehouse_id=transfer_in.to_warehouse_id,
        quantity=transfer_in.quantity,
        status="COMPLETED",
    )
    db.add(transfer)

    db.add(StockMovement(
        product_id=transfer_in.product_id, warehouse_id=transfer_in.from_warehouse_id,
        movement_type="TRANSFER_OUT", quantity=-transfer_in.quantity, reference="transfer",
    ))
    db.add(StockMovement(
        product_id=transfer_in.product_id, warehouse_id=transfer_in.to_warehouse_id,
        movement_type="TRANSFER_IN", quantity=transfer_in.quantity, reference="transfer",
    ))

    db.commit()
    db.refresh(transfer)
    return transfer


@router.get("/transfers", response_model=List[TransferOut])
def list_transfers(db: Session = Depends(get_db)):
    return db.query(Transfer).order_by(Transfer.created_at.desc()).all()
