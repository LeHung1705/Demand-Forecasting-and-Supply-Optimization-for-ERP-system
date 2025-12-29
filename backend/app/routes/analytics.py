from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.services.analytics_service import (
    resolve_range_by_max_dt,
    get_trends_sales_by_day,
    get_dashboard_data,
    get_accuracy_data,
    get_sales_date_bounds,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    time_range: str = Query("30d", regex="^(7d|30d|90d)$"),
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
):
    if to_date is None or from_date is None:
        resolved_from, resolved_to, bounds = resolve_range_by_max_dt(
            time_range=time_range, store_id=store_id, product_id=product_id
        )
        if resolved_to is None or resolved_from is None:
            return {"meta": {"bounds": bounds, "message": "sales table has no data"}, "kpis": {}, "trend": {}}
        from_date, to_date = resolved_from, resolved_to
    else:
        bounds = get_sales_date_bounds(store_id=store_id, product_id=product_id)

    data = get_dashboard_data(from_date, to_date, store_id=store_id, product_id=product_id)

    return {
        "meta": {
            "time_range": time_range,
            "bounds": bounds,
            "from_date": str(from_date),
            "to_date": str(to_date),
            "store_id": store_id,
            "product_id": product_id,
        },
        **data,
    }


@router.get("/trends")
def trends(
    metric: str = "sales_by_day",
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    time_range: str = Query("30d", regex="^(7d|30d|90d)$"),
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
):
    if to_date is None or from_date is None:
        resolved_from, resolved_to, bounds = resolve_range_by_max_dt(
            time_range=time_range, store_id=store_id, product_id=product_id
        )
        if resolved_to is None or resolved_from is None:
            return {"metric": metric, "meta": {"bounds": bounds}, "points": []}
        from_date, to_date = resolved_from, resolved_to
    else:
        bounds = get_sales_date_bounds(store_id=store_id, product_id=product_id)

    if metric == "sales_by_day":
        points = get_trends_sales_by_day(from_date, to_date, store_id=store_id, product_id=product_id)
        return {
            "metric": metric,
            "meta": {
                "time_range": time_range,
                "bounds": bounds,
                "from_date": str(from_date),
                "to_date": str(to_date),
                "store_id": store_id,
                "product_id": product_id,
            },
            "points": points,
        }

    return {"metric": metric, "meta": {"bounds": bounds}, "points": []}


@router.get("/accuracy")
def accuracy(
    time_range: str = "30d",
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
):
    return get_accuracy_data(time_range=time_range, store_id=store_id, product_id=product_id)