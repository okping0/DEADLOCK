import os
os.environ["DATABASE_URL"] = "sqlite:///./test_day3.db"

from datetime import datetime, timedelta, timezone
from app.core.database import Base, engine, SessionLocal
from app.models import inventory, sales, purchasing, user  # noqa
from app.models.inventory import Category, Warehouse, Product, Stock, StockMovement, Supplier, ProductSupplier
from app.ml.intelligence import build_stockout_report, get_avg_daily_demand, calculate_stockout_risk

Base.metadata.create_all(bind=engine)
db = SessionLocal()

wh = Warehouse(name="Main WH")
db.add(wh)
db.flush()

supplier = Supplier(name="ABC Electronics", avg_lead_time_days=10)
db.add(supplier)
db.flush()

# Product A: HIGH risk - low stock, high demand, long lead time
prod_a = Product(sku="CHG-001", name="Laptop Charger", unit_price=1200, unit_cost=700, safety_stock=10)
db.add(prod_a)
db.flush()
db.add(ProductSupplier(product_id=prod_a.id, supplier_id=supplier.id, supplier_price=700, lead_time_days=10, is_preferred=True))
db.add(Stock(product_id=prod_a.id, warehouse_id=wh.id, quantity=23))

# Product B: LOW risk - high stock, low demand
prod_b = Product(sku="MOU-001", name="Wireless Mouse", unit_price=500, unit_cost=250, safety_stock=5)
db.add(prod_b)
db.flush()
db.add(ProductSupplier(product_id=prod_b.id, supplier_id=supplier.id, supplier_price=250, lead_time_days=5, is_preferred=True))
db.add(Stock(product_id=prod_b.id, warehouse_id=wh.id, quantity=200))

db.commit()

# simulate 30 days of sales history: Product A sells ~18/week (~2.57/day), Product B sells ~7/week (~1/day)
now = datetime.now(timezone.utc)
for day in range(30):
    ts = now - timedelta(days=day)
    # Product A: sell ~2-3 units/day
    db.add(StockMovement(
        product_id=prod_a.id, warehouse_id=wh.id, movement_type="OUT",
        quantity=-3, reference="test_sale", created_at=ts,
    ))
    # Product B: sell ~1 unit every 3 days
    if day % 3 == 0:
        db.add(StockMovement(
            product_id=prod_b.id, warehouse_id=wh.id, movement_type="OUT",
            quantity=-1, reference="test_sale", created_at=ts,
        ))
db.commit()

print("=== Avg daily demand ===")
demand_a = get_avg_daily_demand(db, prod_a.id, wh.id, lookback_days=30)
demand_b = get_avg_daily_demand(db, prod_b.id, wh.id, lookback_days=30)
print(f"Product A (charger): {demand_a} units/day -> {round(demand_a*7,1)} units/week")
print(f"Product B (mouse):   {demand_b} units/day -> {round(demand_b*7,1)} units/week")

print("\n=== Full stockout report ===")
report = build_stockout_report(db, warehouse_id=wh.id)
for item in report:
    print(item)

db.close()
