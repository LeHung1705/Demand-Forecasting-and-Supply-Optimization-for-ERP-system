# app/routes/planning.py
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.planning_service import generate_replenishment_plan

router = APIRouter(prefix="/planning", tags=["planning"])

@router.get("/replenishment")
def api_replenishment_plan(
    time_range: str = "30d",         # '7d'|'30d'|'90d'
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
):
    return generate_replenishment_plan(
        db=db,
        time_range=time_range,
        store_id=store_id,
        product_id=product_id,
        page=page,
        page_size=page_size,
    )
