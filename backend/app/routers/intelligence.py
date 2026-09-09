from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ml.intelligence import build_stockout_report
from app.ml.forecasting import forecast_demand
from app.models.inventory import Product, Stock

router = APIRouter(prefix="/intelligence", tags=["Intelligence"], dependencies=[Depends(get_current_user)])


@router.get("/stockout-risk")
def stockout_risk(warehouse_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Returns per-product stockout risk, sorted HIGH -> MEDIUM -> LOW.
    This is the core 'smart' feature — turns raw stock counts into an
    actionable risk + reorder recommendation.
    """
    report = build_stockout_report(db, warehouse_id)
    return {
        "total_products": len(report),
        "high_risk_count": sum(1 for r in report if r["stockout_risk"] == "HIGH"),
        "medium_risk_count": sum(1 for r in report if r["stockout_risk"] == "MEDIUM"),
        "items": report,
    }

@router.get("/forecast/{product_id}")
def get_forecast(product_id: int, warehouse_id: int, horizon_days: int = 30, db: Session = Depends(get_db)):
    """Predicted demand for a single product over the next `horizon_days`."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    result = forecast_demand(db, product_id, warehouse_id, horizon_days)

    stock = db.query(Stock).filter(
        Stock.product_id == product_id, Stock.warehouse_id == warehouse_id
    ).first()
    current_stock = stock.quantity if stock else 0

    return {
        "product_id": product.id,
        "sku": product.sku,
        "product_name": product.name,
        "current_stock": current_stock,
        "horizon_days": horizon_days,
        **result,
    }

