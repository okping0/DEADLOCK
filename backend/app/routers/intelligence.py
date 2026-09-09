from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ml.intelligence import build_stockout_report

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
