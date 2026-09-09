"""
Dead Stock & Overstock Intelligence — the headline feature.

Classifies every product into FAST_MOVING / NORMAL / SLOW_MOVING / DEAD_STOCK
based on turnover, then quantifies the money problem: how much capital is
tied up, and what to do about it.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.models.inventory import Stock, Product, StockMovement
from app.ml.intelligence import get_avg_daily_demand

FAST_MOVING_MAX_DAYS = 30
NORMAL_MAX_DAYS = 90
SLOW_MOVING_MAX_DAYS = 180

DEAD_STOCK_NO_SALE_LOOKBACK_DAYS = 60


def classify_product(db: Session, product: Product, stock: Stock, lookback_days: int = 90) -> dict:
    avg_daily_demand = get_avg_daily_demand(db, product.id, stock.warehouse_id, lookback_days)

    since = datetime.now(timezone.utc) - timedelta(days=DEAD_STOCK_NO_SALE_LOOKBACK_DAYS)
    recent_sale_exists = db.query(StockMovement).filter(
        StockMovement.product_id == product.id,
        StockMovement.warehouse_id == stock.warehouse_id,
        StockMovement.movement_type == "OUT",
        StockMovement.created_at >= since,
    ).first() is not None

    if stock.quantity == 0:
        return {
            "classification": "OUT_OF_STOCK",
            "days_of_stock": 0,
            "avg_daily_demand": avg_daily_demand,
            "holding_value": 0.0,
        }

    if not recent_sale_exists:
        classification = "DEAD_STOCK"
        days_of_stock = None
    elif avg_daily_demand <= 0:
        classification = "DEAD_STOCK"
        days_of_stock = None
    else:
        days_of_stock = stock.quantity / avg_daily_demand
        if days_of_stock <= FAST_MOVING_MAX_DAYS:
            classification = "FAST_MOVING"
        elif days_of_stock <= NORMAL_MAX_DAYS:
            classification = "NORMAL"
        elif days_of_stock <= SLOW_MOVING_MAX_DAYS:
            classification = "SLOW_MOVING"
        else:
            classification = "DEAD_STOCK"

    holding_value = round(stock.quantity * product.unit_cost, 2)

    return {
        "classification": classification,
        "days_of_stock": round(days_of_stock, 1) if days_of_stock is not None else None,
        "avg_daily_demand": avg_daily_demand,
        "holding_value": holding_value,
    }


def recommend_action(classification: str, days_of_stock, unit_price: float, unit_cost: float) -> str:
    margin_pct = ((unit_price - unit_cost) / unit_price * 100) if unit_price > 0 else 0

    if classification == "DEAD_STOCK":
        return "Return to supplier if possible, or heavily discount (60%+) to recover partial capital"
    if classification == "SLOW_MOVING":
        if margin_pct > 40:
            return "Discount 15-25% to accelerate turnover, or bundle with a fast-moving product"
        return "Transfer to a warehouse with higher demand for this product, or bundle promotion"
    if classification == "OUT_OF_STOCK":
        return "Reorder — no stock currently held"
    return "No action needed — turnover is healthy"


def build_dead_stock_report(db: Session, warehouse_id: int = None, lookback_days: int = 90) -> dict:
    query = db.query(Stock)
    if warehouse_id is not None:
        query = query.filter(Stock.warehouse_id == warehouse_id)
    stock_rows = query.all()

    items = []
    for stock in stock_rows:
        product = db.query(Product).filter(Product.id == stock.product_id).first()
        if not product or not product.is_active:
            continue

        result = classify_product(db, product, stock, lookback_days)
        action = recommend_action(
            result["classification"], result["days_of_stock"], product.unit_price, product.unit_cost
        )

        items.append({
            "product_id": product.id,
            "sku": product.sku,
            "product_name": product.name,
            "warehouse_id": stock.warehouse_id,
            "current_stock": stock.quantity,
            "unit_cost": product.unit_cost,
            "unit_price": product.unit_price,
            "classification": result["classification"],
            "days_of_stock": result["days_of_stock"],
            "avg_daily_demand": result["avg_daily_demand"],
            "holding_value": result["holding_value"],
            "recommended_action": action,
        })

    summary = {
        "FAST_MOVING": {"count": 0, "value": 0.0},
        "NORMAL": {"count": 0, "value": 0.0},
        "SLOW_MOVING": {"count": 0, "value": 0.0},
        "DEAD_STOCK": {"count": 0, "value": 0.0},
        "OUT_OF_STOCK": {"count": 0, "value": 0.0},
    }
    for item in items:
        bucket = summary[item["classification"]]
        bucket["count"] += 1
        bucket["value"] += item["holding_value"]

    for bucket in summary.values():
        bucket["value"] = round(bucket["value"], 2)

    total_inventory_value = round(sum(b["value"] for b in summary.values()), 2)
    recoverable_capital = round(summary["SLOW_MOVING"]["value"] + summary["DEAD_STOCK"]["value"], 2)

    items.sort(key=lambda i: (
        0 if i["classification"] == "DEAD_STOCK" else 1 if i["classification"] == "SLOW_MOVING" else 2,
        -i["holding_value"],
    ))

    return {
        "summary": summary,
        "total_inventory_value": total_inventory_value,
        "recoverable_capital_estimate": recoverable_capital,
        "items": items,
    }
