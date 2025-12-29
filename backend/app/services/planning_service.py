# app/services/planning_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.csv_store import CsvDuckStore


_store = CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH, settings.CSV_IMPUTED_PATH)


def generate_replenishment_plan(
    time_range: str = "30d",
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 100,
) -> Dict[str, Any]:
    from_date, to_date, bounds = _store.resolve_time_range_by_max_dt(
        time_range=time_range, store_id=store_id, product_id=product_id
    )

    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 100), 500), 1)
    offset = (page - 1) * page_size

    if not from_date or not to_date:
        return {
            "meta": {"time_range": time_range, "bounds": bounds, "page": page, "page_size": page_size, "total_count": 0},
            "data": [],
            "count": 0,
        }

    # Filters
    where = []
    args: List[Any] = [from_date, to_date]
    if store_id is not None:
        where.append("store_id = ?")
        args.append(int(store_id))
    if product_id is not None:
        where.append("product_id = ?")
        args.append(int(product_id))
    where_sql = (" AND " + " AND ".join(where)) if where else ""

    # Count distinct (store_id, product_id) in range
    total_count = _store.query(
        f"""
        WITH daily AS (
          SELECT store_id, product_id, dt, SUM(sale_amount) AS daily_value
          FROM sales
          WHERE dt BETWEEN ? AND ? {where_sql}
          GROUP BY store_id, product_id, dt
        )
        SELECT COUNT(*) AS n FROM (SELECT store_id, product_id FROM daily GROUP BY store_id, product_id) t
        """,
        args,
    )[0]["n"]

    rows = _store.query(
        f"""
        WITH daily AS (
            SELECT
                store_id,
                product_id,
                dt,
                SUM(TRY_CAST(sale_amount AS DOUBLE)) AS daily_value
            FROM sales
            WHERE dt BETWEEN ? AND ? {where_sql}
            GROUP BY store_id, product_id, dt
        ),
        inv AS (
            SELECT
                store_id,
                product_id,
                COALESCE(MAX(TRY_CAST(stock_hour6_22_cnt AS INTEGER)), 0) AS stock_hours,
                COALESCE(MAX(TRY_CAST(hours_stock_status AS INTEGER)), 0) AS stock_status_total
            FROM sales
            WHERE dt BETWEEN ? AND ? {where_sql}
            GROUP BY store_id, product_id
        )
        SELECT
            d.store_id,
            d.product_id,
            AVG(d.daily_value) AS avg_daily_sales,
            COALESCE(i.stock_hours, 0) AS stock_availability,
            COALESCE(i.stock_status_total, 0) AS stock_status_total
        FROM daily d
        LEFT JOIN inv i ON i.store_id = d.store_id AND i.product_id = d.product_id
        GROUP BY d.store_id, d.product_id, i.stock_hours, i.stock_status_total
        ORDER BY avg_daily_sales DESC
        LIMIT ? OFFSET ?
        """,
        # params: daily-range + filters, then inv-range + filters, then limit/offset
        [*args, *args, page_size, offset],
    )


    LEAD_TIME_DAYS = 7.0
    out: List[Dict[str, Any]] = []

    for r in rows:
        avg_sales = float(r["avg_daily_sales"] or 0.0)
        stock_hours = int(r["stock_availability"] or 0)
        coverage = stock_hours / 16.0

        risk_level = "low"
        status = "Ổn định"
        safety = 1.0
        if stock_hours < 5:
            risk_level = "high"
            status = "Cần nhập gấp (Critical)"
            safety = 1.5
        elif stock_hours < 12:
            risk_level = "medium"
            status = "Cần bổ sung (Warning)"
            safety = 1.2

        base_need = avg_sales * max(0.0, (LEAD_TIME_DAYS - coverage))
        suggested = base_need * safety

        out.append(
            {
                "store_id": int(r["store_id"]),
                "product_id": int(r["product_id"]),
                "avg_daily_sales": round(avg_sales, 2),  # VALUE-based
                "stock_availability_hours": stock_hours,
                "status": status,
                "risk_level": risk_level,
                "suggested_replenishment": round(float(suggested), 2),  # VALUE-based
            }
        )

    return {
        "meta": {
            "time_range": time_range,
            "from_date": str(from_date),
            "to_date": str(to_date),
            "bounds": bounds,
            "store_id": store_id,
            "product_id": product_id,
            "page": page,
            "page_size": page_size,
            "total_count": int(total_count or 0),
            "note": "suggested_replenishment is VALUE (sale_amount-based), not quantity",
        },
        "data": out,
        "count": len(out),
    }
