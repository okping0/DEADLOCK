"""
Core intelligence functions — demand estimation and stockout risk scoring.
Kept separate from routers so Day 4/5 forecasting and dead-stock modules
can reuse these without duplicating query logic.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app.models.inventory import StockMovement, Product, Stock, Supplier, ProductSupplier


def get_avg_daily_demand(db: Session, product_id: int, warehouse_id: int, lookback_days: int = 90) -> float:
    """
    Average daily units sold, based on OUT movements (sales) over the lookback
    window. OUT movements are stored as negative quantities, so we sum and
    flip sign.

    Divides by the ACTUAL span of history available, not a fixed window —
    a product with only 10 days of sales history would otherwise have its
    demand diluted by dividing by a fixed 90, making it look artificially
    slow-moving. Returns 0.0 if there's no sales history at all.
    """
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    earliest = db.query(func.min(StockMovement.created_at)).filter(
        StockMovement.product_id == product_id,
        StockMovement.warehouse_id == warehouse_id,
        StockMovement.movement_type == "OUT",
        StockMovement.created_at >= since,
    ).scalar()

    if earliest is None:
        return 0.0

    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=timezone.utc)
    actual_days = max((datetime.now(timezone.utc) - earliest).days, 1)

    total_out = db.query(func.sum(StockMovement.quantity)).filter(
        StockMovement.product_id == product_id,
        StockMovement.warehouse_id == warehouse_id,
        StockMovement.movement_type == "OUT",
        StockMovement.created_at >= since,
    ).scalar()

    total_out = abs(total_out) if total_out else 0
    return round(total_out / actual_days, 2)


def get_best_supplier_lead_time(db: Session, product_id: int) -> int:
    """
    Returns the lead time (days) to use for reorder calculations — the
    preferred supplier's lead time if one is set, otherwise the fastest
    available supplier for this product. Falls back to 14 days if the
    product has no linked supplier yet.
    """
    preferred = db.query(ProductSupplier).filter(
        ProductSupplier.product_id == product_id, ProductSupplier.is_preferred == True  # noqa: E712
    ).first()
    if preferred:
        return preferred.lead_time_days

    fastest = db.query(ProductSupplier).filter(
        ProductSupplier.product_id == product_id
    ).order_by(ProductSupplier.lead_time_days.asc()).first()
    if fastest:
        return fastest.lead_time_days

    return 14  # sensible default when no supplier is linked yet


def calculate_stockout_risk(current_stock: int, avg_daily_demand: float, lead_time_days: int) -> dict:
    """
    Core risk formula: compare how many days current stock will last against
    how long it takes to get more (lead time).

    days_of_stock < lead_time            -> HIGH   (will run out before reorder arrives)
    days_of_stock < lead_time * 1.5      -> MEDIUM (cutting it close)
    otherwise                            -> LOW
    """
    if avg_daily_demand <= 0:
        # no recent sales velocity — can't run out on demand alone
        return {"days_of_stock": None, "risk_level": "LOW"}

    days_of_stock = round(current_stock / avg_daily_demand, 1)

    if days_of_stock < lead_time_days:
        risk = "HIGH"
    elif days_of_stock < lead_time_days * 1.5:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {"days_of_stock": days_of_stock, "risk_level": risk}


def recommended_order_quantity(avg_daily_demand: float, lead_time_days: int, safety_stock: int, current_stock: int) -> int:
    """
    Classic reorder formula:
    order enough to cover demand during lead time + safety stock, minus what's already on hand.
    Never negative.
    """
    target = (avg_daily_demand * lead_time_days) + safety_stock
    qty = round(target - current_stock)
    return max(qty, 0)


def build_stockout_report(db: Session, warehouse_id: int = None) -> list:
    """
    Full per-product stockout risk report. If warehouse_id is given, scoped
    to that warehouse; otherwise runs across all stock rows.
    """
    query = db.query(Stock)
    if warehouse_id is not None:
        query = query.filter(Stock.warehouse_id == warehouse_id)
    stock_rows = query.all()

    report = []
    for stock in stock_rows:
        product = db.query(Product).filter(Product.id == stock.product_id).first()
        if not product or not product.is_active:
            continue

        avg_demand = get_avg_daily_demand(db, stock.product_id, stock.warehouse_id)
        lead_time = get_best_supplier_lead_time(db, stock.product_id)
        risk = calculate_stockout_risk(stock.quantity, avg_demand, lead_time)
        reorder_qty = recommended_order_quantity(avg_demand, lead_time, product.safety_stock, stock.quantity)

        report.append({
            "product_id": product.id,
            "sku": product.sku,
            "product_name": product.name,
            "warehouse_id": stock.warehouse_id,
            "current_stock": stock.quantity,
            "avg_daily_demand": avg_demand,
            "avg_weekly_demand": round(avg_demand * 7, 1),
            "lead_time_days": lead_time,
            "days_of_stock": risk["days_of_stock"],
            "stockout_risk": risk["risk_level"],
            "recommended_order_qty": reorder_qty,
        })

    # surface the riskiest products first
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    report.sort(key=lambda r: risk_order[r["stockout_risk"]])
    return report
