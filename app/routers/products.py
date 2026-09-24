from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[schemas.ProductOut])
def list_products(
    search: str | None = Query(default=None, description="Matches name, SKU, or barcode"),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return crud.list_products(db, search=search, category=category)


@router.get("/next-sku", response_model=schemas.NextSkuOut)
def next_sku(db: Session = Depends(get_db)):
    """Returns a guaranteed-unique, human-readable SKU (KS-1000, KS-1001, ...)
    for the "Auto-Gen" button. Must stay ABOVE /{product_id} below, or FastAPI
    would try to match "next-sku" as a product id."""
    return {"sku": crud.next_sku(db)}


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    try:
        return crud.get_product(db, product_id)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))


@router.post("", response_model=schemas.ProductOut, status_code=201)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_product(db, payload)
    except crud.DuplicateSKU as e:
        raise HTTPException(409, str(e))


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: str, payload: schemas.ProductUpdate, db: Session = Depends(get_db)):
    try:
        return crud.update_product(db, product_id, payload)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))
    except crud.DuplicateSKU as e:
        raise HTTPException(409, str(e))


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: str, db: Session = Depends(get_db)):
    try:
        crud.delete_product(db, product_id)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))
    except IntegrityError:
        # Safety net: this fires only if the one-time Aiven migration for
        # ON DELETE SET NULL hasn't been run yet.
        raise HTTPException(
            409,
            "This product still has linked sales or purchase-order records. "
            "Run the database migration (see setup notes) to allow deleting "
            "products that already have history.",
        )


@router.post("/{product_id}/sell", response_model=schemas.SaleTransactionOut)
def sell_variant(product_id: str, payload: schemas.SellVariantRequest, db: Session = Depends(get_db)):
    """Sells exactly 1 unit of one color/size variant."""
    try:
        return crud.sell_variant(db, product_id, payload.variant_id)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))
    except crud.InsufficientStock as e:
        raise HTTPException(409, f"{e.label} is out of stock")


@router.post("/{product_id}/restock", response_model=schemas.ProductOut)
def restock_variant(product_id: str, payload: schemas.RestockVariantRequest, db: Session = Depends(get_db)):
    try:
        return crud.restock_variant(db, product_id, payload.variant_id, payload.amount)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))


@router.post("/{product_id}/adjust", response_model=schemas.ProductOut)
def adjust_stock(product_id: str, payload: schemas.AdjustRequest, db: Session = Depends(get_db)):
    try:
        return crud.adjust_stock(db, product_id, payload.delta)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))


@router.post("/bulk-restock", response_model=list[schemas.ProductOut])
def bulk_restock(payload: schemas.BulkRestockRequest, db: Session = Depends(get_db)):
    try:
        return crud.bulk_restock(db, payload.items)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))
