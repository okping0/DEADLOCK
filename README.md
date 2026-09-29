# Smart Inventory & Demand Forecasting ERP

An ERP system that goes beyond raw stock counts — it predicts demand, scores
stockout risk, and identifies dead/overstocked inventory tying up capital.

Instead of showing:
```
Laptop Charger: 23 units
```

It shows:
```
Laptop Charger
Current stock: 23
Avg weekly demand: 22
Stockout risk: HIGH
Recommended order: 18 units
```

## Stack

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL
- **ML:** statsmodels (Holt Exponential Smoothing) for demand forecasting,
  custom classification logic for dead-stock detection
- **Frontend:** React (Vite), Recharts

## Headline feature: Dead Stock & Overstock Intelligence

Classifies every product as `FAST_MOVING` / `NORMAL` / `SLOW_MOVING` /
`DEAD_STOCK` based on turnover, quantifies how much capital is tied up in
each bucket, and recommends an action (discount, transfer, return to
supplier) based on margin and movement.

## Other features

- **Stockout risk scoring** — HIGH / MEDIUM / LOW based on current stock vs.
  sales velocity vs. supplier lead time, with a recommended reorder quantity
- **Demand forecasting** — predicts units needed over the next N days per
  product, using Holt's Exponential Smoothing (captures trend, not just averages)
- Full inventory/sales/purchasing CRUD with stock movement audit trail
- JWT authentication

## Running it

### Option A — Docker (recommended, one command)

```bash
docker compose up --build
```

This starts Postgres, the backend (`:8000`), and the frontend (`:5173`) together.
Once it's up, seed realistic demo data:

```bash
docker compose exec backend python seed.py
```

Then open http://localhost:5173, register a user, and log in.

### Option B — Running manually

**1. Postgres**
Install PostgreSQL locally and create a database named `erp_db` (or run
`docker run --name erp-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=erp_db -p 5432:5432 -d postgres:16`).

**2. Backend**
```bash
cd backend
cp .env.example .env      # adjust DATABASE_URL if needed
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Tables auto-create on first run. Then seed demo data:
```bash
python seed.py
```

**3. Frontend**
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173, register a user via the API or a `/auth/register`
call, then log in.

## API overview

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login` |
| Products | `GET/POST /products/`, `GET/PUT/DELETE /products/{id}` |
| Categories, Suppliers, Warehouses | full CRUD |
| Stock | `GET /stock/`, `POST /stock/adjust`, `POST /stock/transfer` |
| Sales | `POST /sales-orders/` (auto-deducts stock), `GET /sales-orders/` |
| Purchasing | `POST /purchase-orders/`, `POST /purchase-orders/{id}/receive` (supports partial receiving) |
| **Intelligence** | `GET /intelligence/stockout-risk`, `GET /intelligence/forecast/{product_id}`, `GET /intelligence/dead-stock` |

Interactive API docs available at `http://localhost:8000/docs` once the
backend is running.

## Project structure

```
backend/
  app/
    core/        # DB config, security, auth dependency
    models/      # SQLAlchemy models
    schemas/     # Pydantic request/response schemas
    routers/     # API endpoints
    ml/          # forecasting, stockout risk, dead-stock logic
  seed.py        # generates realistic historical data for the ML models
frontend/
  src/
    pages/       # Login, Dashboard
    api.js       # API client
```
