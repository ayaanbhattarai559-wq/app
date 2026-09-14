from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[schemas.NotificationOut])
def list_notifications(db: Session = Depends(get_db)):
    return crud.list_notifications(db)


@router.post("/mark-all-read", status_code=204)
def mark_all_read(db: Session = Depends(get_db)):
    crud.mark_all_read(db)
