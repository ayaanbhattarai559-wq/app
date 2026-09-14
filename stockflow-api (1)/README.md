# StockFlow API

FastAPI + MySQL backend for the StockFlow inventory/POS frontend
(the app you built in Google AI Studio). It replaces `localStorage` with a
real database and mirrors every action currently in `App.tsx`
(`handleSoldQuick`, `handleCompleteSale`, `handleReceiveShipment`, etc.) as
an API endpoint.

## 1. Set up MySQL

```sql
CREATE DATABASE stockflow CHARACTER SET utf8mb4;
CREATE USER 'stockflow'@'%' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON stockflow.* TO 'stockflow'@'%';
FLUSH PRIVILEGES;
```

(`schema.sql` has the full table definitions if you want to create them by
hand instead of letting the app do it — see `AUTO_CREATE_TABLES` below.)

## 2. Configure

```bash
cp .env.example .env
# edit .env with your real DB credentials and frontend URL
```

## 3. Install & run

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first startup, with the default `.env`, the app creates all tables and
seeds them with the same 8 products / 3 purchase orders / 3 notifications
your mock data (`mockData.ts`) shipped with — so the app looks identical to
what you've been testing against, just backed by MySQL now.

Interactive API docs: `http://localhost:8000/docs`

## Endpoints

| Frontend action (`App.tsx`)     | Endpoint                                  |
|----------------------------------|--------------------------------------------|
| Load catalog                     | `GET /products`                            |
| `handleSoldQuick`                 | `POST /products/{id}/sell`                 |
| `handleRestockQuick`              | `POST /products/{id}/restock`              |
| `handleBatchAdjust`               | `POST /products/{id}/adjust`               |
| `handleSaveProduct` (new)         | `POST /products`                           |
| `handleSaveProduct` (edit)        | `PUT /products/{id}`                       |
| `handleCompleteSale`              | `POST /sales/checkout`                     |
| Recent sales list                 | `GET /sales/recent`                        |
| `handleReceiveShipment`           | `POST /purchase-orders/{id}/receive`       |
| `handleBulkRestockLowItems`       | `POST /products/bulk-restock`              |
| Notifications bell                | `GET /notifications`                       |
| Mark all read                     | `POST /notifications/mark-all-read`        |
| Today's units/revenue tiles       | `GET /analytics/today`                     |

## Wiring up the frontend

Right now `App.tsx` keeps all state in `useState` + `localStorage`. To
switch it over:

1. Replace the `useState(() => localStorage.getItem(...))` initializers with
   a `useEffect` that calls `GET /products`, `GET /sales/recent`, etc. on
   mount and populates state from the response.
2. Replace each handler's local array mutation (`setProducts(prev => ...)`)
   with a `fetch()` call to the matching endpoint above, then update state
   from the response instead of computing it locally — the backend is now
   the source of truth for stock counts, sold counts, and totals.
3. Drop the `localStorage.setItem` sync `useEffect` entirely.
4. Set `CORS_ORIGINS` in `.env` to wherever the frontend is served from
   (e.g. `http://localhost:5173` for Vite's dev server).

I can do this wiring for you as a follow-up if you'd like — just say so.

## The hard part: concurrent stock updates

A POS system has one classic race condition: two terminals (or two rapid
taps on the same quick-sell tile) both read `stock = 1`, both decide "OK to
sell," and both decrement — stock goes to -1 and you've sold an item you
don't have. Two ways to handle it:

**Pessimistic locking (what this backend uses).** Every stock-changing
operation runs `SELECT ... FOR UPDATE` inside a transaction before touching
the row, so MySQL makes the second concurrent request wait for the first to
commit or roll back, then re-reads the now-current stock. Simple to reason
about, and correct by construction. Cost: under heavy concurrent load on the
*same* product, requests queue up behind the lock instead of running in
parallel.

**Optimistic concurrency (the alternative).** Add a `version` integer column;
reads grab the current version, writes do
`UPDATE products SET stock = stock - 1, version = version + 1 WHERE id = ? AND version = ?`
and check `rows_affected == 1` — if 0, someone else won the race and the
client retries. No locks held, so it scales better under contention, but it
pushes retry logic onto the caller and gets awkward for the multi-item
checkout here (you'd need to detect *which* line item lost the race and
retry just that one).

For a single-shop POS, the concurrency on any one product is low (a handful
of terminals, not thousands of concurrent buyers), so pessimistic locking is
the simpler, safer default — that's what's implemented. If this ever becomes
a multi-location or high-traffic e-commerce backend, optimistic concurrency
(or a queue-based stock reservation system) would be worth revisiting.

## Notes / things you'll likely want next

- **Auth**: there's none yet — anyone who can reach the API can sell, restock,
  and edit products. Fine for local dev; add an auth dependency before
  deploying anywhere reachable from the internet.
- **Migrations**: `AUTO_CREATE_TABLES=true` is convenient for getting
  started but doesn't handle schema changes safely. Once this is real,
  switch to Alembic.
- **Barcode scanner**: `BarcodeScannerModal.tsx` matches locally against the
  already-loaded `products` array — no backend change needed there, it'll
  keep working once `products` comes from the API instead of mock data.
