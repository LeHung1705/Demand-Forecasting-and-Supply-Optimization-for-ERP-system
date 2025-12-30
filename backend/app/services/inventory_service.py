from __future__ import annotations

import math
import statistics
from statistics import NormalDist
from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.csv_store import CsvDuckStore
from app.schemas.inventory import InventoryPlanRequest, InventoryPlanResponse


_store = CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH, settings.CSV_IMPUTED_PATH)


def _z_from_service_level(service_level: float) -> float:
    # NormalDist.inv_cdf(0) or inv_cdf(1) is inf/-inf; clamp defensively.
    p = float(service_level)
    p = max(1e-12, min(1.0 - 1e-12, p))
    return float(NormalDist().inv_cdf(p))


def _safe_stdev(xs: List[float]) -> float:
    # Sample stdev if enough points, else 0
    if len(xs) < 2:
        return 0.0
    try:
        return float(statistics.stdev(xs))
    except statistics.StatisticsError:
        return 0.0


def _safe_mean(xs: List[float]) -> float:
    if not xs:
        return 0.0
    return float(statistics.mean(xs))


def build_inventory_plan(req: InventoryPlanRequest) -> InventoryPlanResponse:
    """
    Compute Inventory Suggestion using standard formulas:

    1) Lead-time demand = AvgDailySales * (LeadTimeHours / 24)
    2) Safety stock = Z * StdDevDailySales * sqrt(LeadTimeDays)
    3) ROP = Lead-time demand + Safety stock
    """
    # Resolve time window based on max(dt) in DuckDB, consistent with other services.
    resolved = _store.resolve_time_range_by_max_dt(
        time_range=req.time_range,
        store_id=req.store_id,
        product_id=req.product_id,
        table="sales",
    )
    from_date = resolved.get("from_date")
    to_date = resolved.get("to_date")

    lead_time_days = float(req.lead_time_hours) / 24.0
    z = _z_from_service_level(req.service_level)

    daily_values: List[float] = []
    if from_date and to_date:
        where = ["dt BETWEEN ? AND ?"]
        args: List[Any] = [from_date, to_date]

        if req.store_id is not None:
            where.append("store_id = ?")
            args.append(int(req.store_id))
        if req.product_id is not None:
            where.append("product_id = ?")
            args.append(int(req.product_id))

        where_sql = " AND ".join(where)

        rows = _store.query(
            f"""
            SELECT
              dt,
              SUM(TRY_CAST(sale_amount AS DOUBLE)) AS daily_value
            FROM sales
            WHERE {where_sql}
            GROUP BY dt
            ORDER BY dt
            """,
            args,
        )

        for r in rows:
            v = r.get("daily_value")
            try:
                daily_values.append(float(v or 0.0))
            except Exception:
                daily_values.append(0.0)

    avg_daily = _safe_mean(daily_values)
    sd_daily = _safe_stdev(daily_values)

    lead_time_demand = avg_daily * lead_time_days
    safety_stock = z * sd_daily * math.sqrt(max(0.0, lead_time_days))
    reorder_point = lead_time_demand + safety_stock

    # Keep numbers stable/clean in API responses
    metrics: Dict[str, Any] = {
        "lead_time_hours": int(req.lead_time_hours),
        "lead_time_days": round(lead_time_days, 6),
        "service_level": float(req.service_level),
        "z_score": round(float(z), 6),
        "days_count": int(len(daily_values)),
        "avg_daily_sales": round(float(avg_daily), 6),
        "stddev_daily_sales": round(float(sd_daily), 6),
        "lead_time_demand": round(float(lead_time_demand), 6),
        "safety_stock": round(float(safety_stock), 6),
        "reorder_point": round(float(reorder_point), 6),
    }

    return InventoryPlanResponse(
        meta={
            "time_range": req.time_range,
            "from_date": from_date,
            "to_date": to_date,
            "store_id": req.store_id,
            "product_id": req.product_id,
        },
        metrics=metrics,
    )