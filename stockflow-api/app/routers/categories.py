from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return crud.list_categories(db)


@router.post("", response_model=schemas.CategoryOut, status_code=201)
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db, payload)
