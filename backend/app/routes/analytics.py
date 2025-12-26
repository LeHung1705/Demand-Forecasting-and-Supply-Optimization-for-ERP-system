from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
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
    db: Session = Depends(get_db),
    # nếu user truyền from/to thì ưu tiên dùng
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    # nếu không truyền from/to thì dùng time_range để tự tính theo max_dt
    time_range: str = Query("30d", regex="^(7d|30d|90d)$"),
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
):
    if to_date is None or from_date is None:
        resolved_from, resolved_to, bounds = resolve_range_by_max_dt(
            db, time_range=time_range, store_id=store_id, product_id=product_id
        )
        if resolved_to is None or resolved_from is None:
            return {"meta": {"bounds": bounds, "message": "sales table has no data"}, "kpis": {}, "trend": {}}
        from_date, to_date = resolved_from, resolved_to
    else:
        bounds = get_sales_date_bounds(db, store_id=store_id, product_id=product_id)

    data = get_dashboard_data(db, from_date, to_date, store_id=store_id, product_id=product_id)

    # meta để frontend biết dataset bounds + range đang dùng
    return {
        "meta": {
            "time_range": time_range,
            "bounds": bounds,
            "from_date": str(from_date),
            "to_date": str(to_date),
        },
        **data,
    }


@router.get("/trends")
def trends(
    db: Session = Depends(get_db),
    metric: str = "sales_by_day",
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    time_range: str = Query("30d", regex="^(7d|30d|90d)$"),
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
):
    if to_date is None or from_date is None:
        resolved_from, resolved_to, bounds = resolve_range_by_max_dt(
            db, time_range=time_range, store_id=store_id, product_id=product_id
        )
        if resolved_to is None or resolved_from is None:
            return {"metric": metric, "meta": {"bounds": bounds}, "points": []}
        from_date, to_date = resolved_from, resolved_to
    else:
        bounds = get_sales_date_bounds(db, store_id=store_id, product_id=product_id)

    if metric == "sales_by_day":
        points = get_trends_sales_by_day(db, from_date, to_date, store_id=store_id, product_id=product_id)
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


# 2. Cập nhật API Accuracy gọi hàm mới
@router.get("/accuracy")
def accuracy(
    time_range: str = "30d", 
    store_id: Optional[int] = None, 
    product_id: Optional[int] = None, 
    db: Session = Depends(get_db)
):
    # Gọi hàm get_accuracy_data vừa viết ở trên
    return get_accuracy_data(
        db=db, 
        time_range=time_range, 
        store_id=store_id, 
        product_id=product_id
    )