# backend/app/routes/optimization.py
from __future__ import annotations

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.optimization_service import calculate_optimal_supply

router = APIRouter(prefix="/optimize", tags=["optimization"])


class SupplyConstraints(BaseModel):
    budget: float = Field(default=50_000_000, description="Value cap (VND/value)")
    max_inventory: float = Field(default=50_000_000, description="Value cap (because no qty/unit_cost in DB)")
    lead_time: int = Field(default=7, ge=1, le=90)


class OptimizeSupplyRequest(BaseModel):
    time_range: str = Field(default="30d", description="7d|30d|90d")
    store_id: Optional[int] = Field(default=None)
    product_ids: Optional[List[int]] = Field(default=None)
    constraints: SupplyConstraints = Field(default_factory=SupplyConstraints)


@router.post("/supply")
def optimize_supply_chain(payload: OptimizeSupplyRequest, db: Session = Depends(get_db)):
    return calculate_optimal_supply(
        db,
        time_range=payload.time_range,
        store_id=payload.store_id,
        product_ids=payload.product_ids,
        constraints=payload.constraints.model_dump(),
    )


@router.get("/recommendations")
def get_recommendations(
    time_range: str = "30d",
    store_id: Optional[int] = None,
    top_n: int = 20,
    db: Session = Depends(get_db),
):
    # recommendations: chạy optimization nhưng cap rất lớn, rồi lấy top_n
    res = calculate_optimal_supply(
        db,
        time_range=time_range,
        store_id=store_id,
        product_ids=None,
        constraints={"budget": 1e18, "max_inventory": 1e18, "lead_time": 7},
    )
    res["data"] = (res.get("data") or [])[: max(1, min(top_n, 200))]
    res["meta"]["top_n"] = top_n
    return res
