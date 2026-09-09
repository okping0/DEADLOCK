"""
Seed script: populates the database with realistic historical data so the
forecasting models have real patterns to learn from.

Generates:
- Categories, warehouses, suppliers, customers
- ~15 products across categories, each with a distinct demand pattern
  (steady sellers, growing trend, seasonal spikes, slow/dead stock)
- ~6 months of daily sales history per product (with weekday effects + noise)
- Purchase order history to replenish stock realistically
Run with: python seed.py
"""
import os
import random
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/erp_db")

from app.core.database import Base, engine, SessionLocal
from app.models import inventory, sales, purchasing, user  # noqa
from app.models.inventory import Category, Warehouse, Supplier, Product, ProductSupplier, Stock, StockMovement
from app.models.sales import Customer

random.seed(42)  # reproducible dataset

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("Seeding categories...")
categories = [Category(name=n) for n in ["Electronics", "Accessories", "Office Supplies", "Networking"]]
db.add_all(categories)
db.flush()

print("Seeding warehouses...")
warehouses = [
    Warehouse(name="Main Warehouse", location="Gwalior", capacity=10000),
    Warehouse(name="North Branch", location="Delhi", capacity=5000),
    Warehouse(name="South Branch", location="Bangalore", capacity=5000),
]
db.add_all(warehouses)
db.flush()

print("Seeding suppliers...")
suppliers = [
    Supplier(name="ABC Electronics", avg_lead_time_days=10, reliability_score=0.95),
    Supplier(name="TechSource Pvt Ltd", avg_lead_time_days=7, reliability_score=0.9),
    Supplier(name="Global Components", avg_lead_time_days=15, reliability_score=0.85),
]
db.add_all(suppliers)
db.flush()

print("Seeding customers...")
customer_names = ["Rahul Sharma", "Priya Patel", "Amit Kumar", "Sneha Reddy", "Vikram Singh",
                   "Ananya Gupta", "Rohan Mehta", "Kavya Iyer", "Arjun Nair", "Divya Rao"]
customers = [Customer(name=n, email=f"{n.split()[0].lower()}@example.com") for n in customer_names]
db.add_all(customers)
db.flush()

# Product definitions: (name, category_idx, price, cost, demand_pattern)
# demand_pattern: (base_daily_demand, trend_per_day, weekend_multiplier, noise_std)
product_defs = [
    ("Laptop Charger 65W", 0, 1200, 700, (2.5, 0.0, 0.6, 1.0)),       # steady, dips weekends
    ("Wireless Mouse", 1, 500, 250, (4.0, 0.02, 0.8, 1.5)),           # growing trend
    ("USB-C Hub", 1, 1500, 900, (1.8, 0.0, 1.0, 0.8)),                # steady
    ("Mechanical Keyboard", 0, 3500, 2200, (1.2, 0.01, 1.3, 0.7)),    # growing, weekend spike
    ("HDMI Cable 2m", 1, 300, 120, (5.0, -0.01, 0.7, 2.0)),           # declining, high volume
    ("Laptop Stand", 1, 900, 500, (0.8, 0.0, 0.5, 0.5)),              # slow mover
    ("Bluetooth Speaker", 0, 2000, 1100, (1.5, 0.015, 1.5, 1.0)),     # growing, weekend spike
    ("A4 Paper Ream", 2, 250, 150, (6.0, 0.0, 0.3, 2.0)),             # steady office, weekday heavy
    ("Stapler", 2, 150, 70, (0.3, -0.005, 0.4, 0.3)),                 # near dead stock
    ("Whiteboard Marker Pack", 2, 200, 90, (0.5, 0.0, 0.4, 0.4)),     # slow mover
    ("Network Switch 8-port", 3, 2500, 1600, (0.9, 0.005, 0.6, 0.5)), # steady niche
    ("Ethernet Cable 5m", 3, 350, 150, (2.2, 0.0, 0.6, 1.0)),         # steady
    ("WiFi Router AC1200", 3, 2800, 1800, (1.0, 0.01, 0.9, 0.6)),     # growing
    ("Webcam 1080p", 0, 1800, 1000, (1.3, 0.02, 1.2, 0.8)),           # growing, weekend spike
    ("Desk Organizer", 2, 400, 200, (0.2, -0.003, 0.5, 0.2)),         # dead stock candidate
]

print(f"Seeding {len(product_defs)} products with demand patterns...")
products = []
# these products won't get restocked in the final 2 weeks, simulating the
# realistic "we're about to run out and haven't reordered yet" scenario —
# without this, every product just looks comfortably stocked, which defeats
# the point of a stockout-risk feature
no_late_restock_skus = {"SKU-1000", "SKU-1003", "SKU-1006", "SKU-1013"}

for i, (name, cat_idx, price, cost, pattern) in enumerate(product_defs):
    sku = f"SKU-{1000 + i}"
    product = Product(
        sku=sku, name=name, category_id=categories[cat_idx].id,
        unit_price=price, unit_cost=cost,
        reorder_point=random.randint(10, 25), safety_stock=random.randint(5, 15),
    )
    db.add(product)
    db.flush()

    # link to 1-2 suppliers
    primary_supplier = random.choice(suppliers)
    db.add(ProductSupplier(
        product_id=product.id, supplier_id=primary_supplier.id,
        supplier_price=cost, lead_time_days=primary_supplier.avg_lead_time_days,
        is_preferred=True,
    ))

    products.append((product, pattern))

db.commit()

print("Generating ~180 days of sales history per product (Main Warehouse)...")
main_wh = warehouses[0]
today = datetime.now(timezone.utc)
history_days = 180

# initial stock: give each product a realistic starting buffer (~2-3 weeks)
for product, pattern in products:
    base_demand = pattern[0]
    if product.sku in no_late_restock_skus:
        starting_stock = int(base_demand * 10) + 8  # tighter buffer for the "running low" set
    else:
        starting_stock = int(base_demand * 18) + 15
    db.add(Stock(product_id=product.id, warehouse_id=main_wh.id, quantity=starting_stock))
db.commit()

movements = []
for product, pattern in products:
    base_demand, trend, weekend_mult, noise_std = pattern
    stock_row = db.query(Stock).filter(
        Stock.product_id == product.id, Stock.warehouse_id == main_wh.id
    ).first()

    for day_offset in range(history_days, 0, -1):
        day = today - timedelta(days=day_offset)
        is_weekend = day.weekday() >= 5

        expected = base_demand + (trend * (history_days - day_offset))
        expected *= weekend_mult if is_weekend else 1.0
        expected = max(expected, 0)

        qty_sold = max(0, round(random.gauss(expected, noise_std)))
        if qty_sold == 0:
            continue
        qty_sold = min(qty_sold, stock_row.quantity)  # never sell below 0
        if qty_sold == 0:
            continue

        stock_row.quantity -= qty_sold
        movements.append(StockMovement(
            product_id=product.id, warehouse_id=main_wh.id,
            movement_type="OUT", quantity=-qty_sold,
            reference="seed_sale", created_at=day,
        ))

        # restock every 12 days, sized to cover that cycle's demand plus a
        # modest buffer (not a huge stockpile) — keeps stock levels realistic
        # enough that stockout risk scoring actually has HIGH/MEDIUM cases to find.
        # Skip restocking in the final 14 days for the "running low" product set,
        # so the current-moment snapshot has real risk to detect.
        skip_late_restock = product.sku in no_late_restock_skus and day_offset <= 30
        if day_offset % 12 == 0 and not skip_late_restock:
            current_expected = base_demand + (trend * (history_days - day_offset))
            restock_qty = int(current_expected * 12 * 1.2) + 8
            stock_row.quantity += restock_qty
            movements.append(StockMovement(
                product_id=product.id, warehouse_id=main_wh.id,
                movement_type="IN", quantity=restock_qty,
                reference="seed_restock", created_at=day,
            ))

db.add_all(movements)
db.commit()

print(f"Inserted {len(movements)} stock movements across {len(products)} products.")
print("Final stock levels:")
for product, _ in products:
    stock_row = db.query(Stock).filter(
        Stock.product_id == product.id, Stock.warehouse_id == main_wh.id
    ).first()
    print(f"  {product.sku} ({product.name}): {stock_row.quantity} units")

db.close()
print("\nSeed complete.")
