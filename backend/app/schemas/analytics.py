from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# ===== Sales Trend =====
class SalesTrendPoint(BaseModel):
    date: str
    sales: float

class SalesTrendMeta(BaseModel):
    from_date: str
    to_date: str
    store_id: Optional[int] = None
    product_id: Optional[int] = None
    points: int

class SalesTrendResponse(BaseModel):
    meta: SalesTrendMeta
    series: List[SalesTrendPoint]

# ===== Dashboard =====
class DashboardKPI(BaseModel):
    product_count: int
    store_count: int
    total_sales: float

class DashboardResponse(BaseModel):
    kpis: DashboardKPI
    sales_trend: SalesTrendResponse

# ===== Trends =====
class TrendPoint(BaseModel):
    key: str
    value: float

class TrendsResponse(BaseModel):
    metric: str
    from_date: str
    to_date: str
    points: List[TrendPoint]

# ===== Accuracy =====
class AccuracyResponse(BaseModel):
    available: bool
    message: str
    metrics: Optional[Dict[str, Any]] = None
