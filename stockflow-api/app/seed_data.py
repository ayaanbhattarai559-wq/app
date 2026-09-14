"""
The clothing-shop version of the app starts with an empty catalog (a
"blank slate" for a real boutique to fill in) — only the default category
list is seeded, matching the frontend's DEFAULT_CATEGORIES.
"""
from sqlalchemy.orm import Session

from . import crud


def seed(db: Session) -> None:
    crud.seed_default_categories(db)
