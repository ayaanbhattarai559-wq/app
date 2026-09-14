from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/today", response_model=schemas.TodaySummary)
def today_summary(db: Session = Depends(get_db)):
    return crud.today_summary(db)
