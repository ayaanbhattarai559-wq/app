from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/checkout", response_model=schemas.SaleTransactionOut)
def checkout(payload: schemas.CheckoutRequest, db: Session = Depends(get_db)):
    try:
        return crud.checkout(db, payload)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))
    except crud.InsufficientStock as e:
        raise HTTPException(409, f"Only {e.available} of {e.label} left, cart wants {e.requested}")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/recent", response_model=list[schemas.SaleTransactionOut])
def recent_sales(limit: int = Query(default=50, le=200), db: Session = Depends(get_db)):
    return crud.list_recent_sales(db, limit=limit)


@router.delete("/{transaction_id}", status_code=204)
def delete_sale(transaction_id: str, db: Session = Depends(get_db)):
    """Deletes a sale record entirely (e.g. test data). Does not restore
    stock or lower a product's sold count -- do that separately if needed."""
    try:
        crud.delete_sale(db, transaction_id)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))
