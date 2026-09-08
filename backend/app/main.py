from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routers import auth, products, categories, suppliers, warehouses, stock, customers, sales_orders, purchase_orders

# Import all models so Base knows about them before create_all
from app.models import inventory, sales, purchasing, user  # noqa: F401

app = FastAPI(title="Smart Inventory & Demand Forecasting ERP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
app.include_router(warehouses.router)
app.include_router(stock.router)
app.include_router(customers.router)
app.include_router(sales_orders.router)
app.include_router(purchase_orders.router)


@app.get("/")
def root():
    return {"status": "ERP backend running"}
