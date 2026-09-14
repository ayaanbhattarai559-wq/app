from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


@router.get("", response_model=list[schemas.PurchaseOrderOut])
def list_purchase_orders(db: Session = Depends(get_db)):
    return crud.list_purchase_orders(db)


@router.post("", response_model=schemas.PurchaseOrderOut, status_code=201)
def create_purchase_order(payload: schemas.PurchaseOrderCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_purchase_order(db, payload)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))


@router.post("/{po_id}/receive", response_model=schemas.PurchaseOrderOut)
def receive_shipment(po_id: str, db: Session = Depends(get_db)):
    """Restock view 'Verify & Receive' button."""
    try:
        return crud.receive_shipment(db, po_id)
    except crud.NotFound as e:
        raise HTTPException(404, str(e))
