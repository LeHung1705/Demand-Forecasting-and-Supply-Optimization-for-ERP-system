from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.data.csv_store import CsvDuckStore


_store = CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH)


def get_sales_date_bounds(store_id: Optional[int] = None, product_id: Optional[int] = None) -> Dict[str, Any]:
    b = _store.get_bounds(store_id=store_id, product_id=product_id)
    return {"min_dt": b.min_dt, "max_dt": b.max_dt, "available_days": b.available_days}


def resolve_range_by_max_dt(
    time_range: str,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Tuple[Optional[date], Optional[date], Dict[str, Any]]:
    return _store.resolve_time_range_by_max_dt(time_range=time_range, store_id=store_id, product_id=product_id)


def get_trends_sales_by_day(
    from_date: date,
    to_date: date,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    points = _store.aggregate_sales_by_day(from_date, to_date, store_id=store_id, product_id=product_id)
    # Keep existing response shape keys: {"key": "...", "value": ...}
    return [{"key": str(p["key"]), "value": float(p["value"] or 0)} for p in points]


def get_dashboard_data(
    from_date: date,
    to_date: date,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    # product/store counts (global; stable even when filters applied)
    product_count = _store.query("SELECT COUNT(DISTINCT product_id) AS n FROM sales")[0]["n"] or 0
    store_count = _store.query("SELECT COUNT(DISTINCT store_id) AS n FROM sales")[0]["n"] or 0

    # total sales in selected range + filters
    where = []
    params: List[Any] = [from_date, to_date]
    if store_id is not None:
        where.append("store_id = ?")
        params.append(int(store_id))
    if product_id is not None:
        where.append("product_id = ?")
        params.append(int(product_id))
    where_sql = (" AND " + " AND ".join(where)) if where else ""

    total_sales = _store.query(
        f"""
        SELECT COALESCE(SUM(sale_amount), 0) AS total
        FROM sales
        WHERE dt BETWEEN ? AND ? {where_sql}
        """,
        params,
    )[0]["total"]

    trend_points = get_trends_sales_by_day(from_date, to_date, store_id=store_id, product_id=product_id)

    return {
        "kpis": {
            "product_count": int(product_count),
            "store_count": int(store_count),
            "total_sales": float(total_sales or 0),
        },
        "trend": {
            "from_date": str(from_date),
            "to_date": str(to_date),
            "store_id": store_id,
            "product_id": product_id,
            "points": trend_points,
        },
    }


def get_accuracy_data(
    time_range: str = "30d",
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    # Must not 500 in CSV mode
    return {"available": False, "message": "Forecast data not available in CSV mode", "metrics": None}