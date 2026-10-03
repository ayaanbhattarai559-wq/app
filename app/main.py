from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_auth, router as auth_router
from .config import settings
from .database import engine, Base, SessionLocal
from .routers import products, sales, purchase_orders, notifications, analytics, categories
from . import seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_data.seed(db)
        finally:
            db.close()
    yield


app = FastAPI(title="StockFlow API", version="2.0.0", lifespan=lifespan)

# "*" is kept on purpose: the Android app will call this from a different
# origin than the website. Security now comes from the PIN token instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

protected = [Depends(require_auth)]

app.include_router(auth_router)
app.include_router(categories.router, dependencies=protected)
app.include_router(products.router, dependencies=protected)
app.include_router(sales.router, dependencies=protected)
app.include_router(purchase_orders.router, dependencies=protected)
app.include_router(notifications.router, dependencies=protected)
app.include_router(analytics.router, dependencies=protected)


@app.get("/health")
def health():
    return {"status": "ok"}
