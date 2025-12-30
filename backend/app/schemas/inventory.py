from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class InventoryPlanRequest(BaseModel):
    """
    Inventory Suggestion inputs.

    - If store_id/product_id are omitted, the plan is computed for ALL sales (not recommended for big CSVs).
    - time_range is resolved based on max(dt) available in DuckDB (same approach as planning/optimization services).
    """

    time_range: str = Field(default="30d", pattern=r"^(7d|30d|90d)$")
    store_id: Optional[int] = Field(default=None)
    product_id: Optional[int] = Field(default=None)

    lead_time_hours: int = Field(default=24, ge=1, le=24 * 365)
    service_level: float = Field(default=0.95, ge=0.5, lt=1.0)


class InventoryPlanMetrics(BaseModel):
    # Inputs (normalized/derived)
    lead_time_hours: int
    lead_time_days: float
    service_level: float
    z_score: float

    # Stats from history
    days_count: int
    avg_daily_sales: float
    stddev_daily_sales: float

    # Outputs (formulas)
    lead_time_demand: float
    safety_stock: float
    reorder_point: float


class InventoryPlanMeta(BaseModel):
    time_range: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    store_id: Optional[int] = None
    product_id: Optional[int] = None


class InventoryPlanResponse(BaseModel):
    meta: InventoryPlanMeta
    metrics: InventoryPlanMetrics