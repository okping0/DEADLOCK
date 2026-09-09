"""
Demand forecasting — predicts units needed over the next N days per product.

Uses Holt's Exponential Smoothing (statsmodels) when enough history exists
(captures trend, e.g. Wireless Mouse's growing demand), and falls back to a
simple moving average for new products with too little history to fit a
trend model reliably.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import numpy as np
import warnings

from app.models.inventory import StockMovement

MIN_DAYS_FOR_TREND_MODEL = 21  # below this, trend fitting is unreliable — use moving average


def _daily_sales_series(db: Session, product_id: int, warehouse_id: int, lookback_days: int = 180) -> list:
    """
    Returns a list of daily units sold, oldest to newest, with 0-filled gaps
    for days with no sales. This dense, gap-free series is what the
    forecasting model needs — sparse/missing days would bias the trend fit.
    """
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    rows = db.query(StockMovement).filter(
        StockMovement.product_id == product_id,
        StockMovement.warehouse_id == warehouse_id,
        StockMovement.movement_type == "OUT",
        StockMovement.created_at >= since,
    ).all()

    if not rows:
        return []

    daily_totals = {}
    for row in rows:
        day_key = row.created_at.date()
        daily_totals[day_key] = daily_totals.get(day_key, 0) + abs(row.quantity)

    start_date = min(daily_totals.keys())
    end_date = datetime.now(timezone.utc).date()
    series = []
    current = start_date
    while current <= end_date:
        series.append(daily_totals.get(current, 0))
        current += timedelta(days=1)

    return series


def forecast_demand(db: Session, product_id: int, warehouse_id: int, horizon_days: int = 30) -> dict:
    """
    Returns predicted total demand over the next `horizon_days`, plus which
    method was used (so the API response is honest about model confidence).
    """
    series = _daily_sales_series(db, product_id, warehouse_id)

    if len(series) == 0:
        return {
            "predicted_demand": 0,
            "method": "no_history",
            "history_days_used": 0,
            "confidence": "none",
        }

    if len(series) < MIN_DAYS_FOR_TREND_MODEL:
        avg_daily = float(np.mean(series))
        predicted = round(avg_daily * horizon_days)
        return {
            "predicted_demand": predicted,
            "method": "moving_average",
            "history_days_used": len(series),
            "confidence": "low",
        }

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = np.array(series, dtype=float)
            # Holt's linear trend (no seasonality — 180 days of daily data
            # is too short to reliably fit weekly+yearly seasonality together)
            model = ExponentialSmoothing(data, trend="add", damped_trend=True, seasonal=None)
            fit = model.fit()
            forecast_values = fit.forecast(horizon_days)
            forecast_values = np.clip(forecast_values, 0, None)  # demand can't be negative
            predicted = round(float(np.sum(forecast_values)))

        return {
            "predicted_demand": predicted,
            "method": "holt_exponential_smoothing",
            "history_days_used": len(series),
            "confidence": "high" if len(series) >= 90 else "medium",
        }
    except Exception:
        # if the model fails to converge on unusual data, don't break the
        # endpoint — fall back to a safe estimate instead
        avg_daily = float(np.mean(series[-30:])) if len(series) >= 30 else float(np.mean(series))
        predicted = round(avg_daily * horizon_days)
        return {
            "predicted_demand": predicted,
            "method": "moving_average_fallback",
            "history_days_used": len(series),
            "confidence": "low",
        }
