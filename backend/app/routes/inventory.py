from __future__ import annotations

from fastapi import APIRouter

from app.schemas.inventory import InventoryPlanRequest, InventoryPlanResponse
from app.services.inventory_service import build_inventory_plan

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/plan", response_model=InventoryPlanResponse)
def inventory_plan(payload: InventoryPlanRequest) -> InventoryPlanResponse:
    return build_inventory_plan(payload)