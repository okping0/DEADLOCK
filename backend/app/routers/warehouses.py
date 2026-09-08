from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.inventory import Warehouse
from app.schemas.inventory import WarehouseCreate, WarehouseOut

router = APIRouter(prefix="/warehouses", tags=["Warehouses"], dependencies=[Depends(get_current_user)])


@router.post("/", response_model=WarehouseOut)
def create_warehouse(warehouse_in: WarehouseCreate, db: Session = Depends(get_db)):
    warehouse = Warehouse(**warehouse_in.model_dump())
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.get("/", response_model=List[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db)):
    return db.query(Warehouse).all()


@router.delete("/{warehouse_id}")
def delete_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    db.delete(warehouse)
    db.commit()
    return {"detail": "Warehouse deleted"}
