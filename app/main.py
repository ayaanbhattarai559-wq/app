from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(purchase_orders.router)
app.include_router(notifications.router)
app.include_router(analytics.router)


@app.get("/health")
def health():
    return {"status": "ok"}
