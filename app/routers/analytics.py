
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/today", response_model=schemas.TodaySummary)
def today_summary(db: Session = Depends(get_db)):
    return crud.today_summary(db)


@router.get("/history", response_model=list[schemas.TimeSeriesPoint])
def history(
    period: schemas.TimeframePeriod = Query("week"),
    db: Session = Depends(get_db),
):
    return crud.get_time_series(db, period)
