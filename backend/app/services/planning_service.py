# app/services/planning_service.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text


def _resolve_range_by_sales_max_dt(
    db: Session,
    time_range: str,  # '7d'|'30d'|'90d'
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Chuẩn ERP-demo: range bám theo MAX(dt) của sales (theo filter).
    Trả về: {from_date, to_date, bounds{min_dt,max_dt,available_days}}
    """
    bounds_sql = """
    SELECT
      MIN(dt) AS min_dt,
      MAX(dt) AS max_dt,
      COUNT(DISTINCT dt) AS available_days
    FROM sales
    WHERE (:store_id IS NULL OR store_id = :store_id)
      AND (:product_id IS NULL OR product_id = :product_id)
    """
    b = db.execute(text(bounds_sql), {"store_id": store_id, "product_id": product_id}).mappings().first()
    if not b or b["max_dt"] is None:
        return {
            "from_date": None,
            "to_date": None,
            "bounds": {"min_dt": None, "max_dt": None, "available_days": 0},
        }

    max_dt = date.fromisoformat(str(b["max_dt"]))
    min_dt = date.fromisoformat(str(b["min_dt"])) if b["min_dt"] is not None else None

    days = 7
    if time_range == "30d":
        days = 30
    elif time_range == "90d":
        days = 90

    from_dt = max_dt - timedelta(days=days - 1)
    if min_dt and from_dt < min_dt:
        from_dt = min_dt

    return {
        "from_date": from_dt,
        "to_date": max_dt,
        "bounds": {
            "min_dt": str(b["min_dt"]),
            "max_dt": str(b["max_dt"]),
            "available_days": int(b["available_days"] or 0),
        },
    }


def generate_replenishment_plan(
    db: Session,
    time_range: str = "30d",
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 100,
) -> Dict[str, Any]:
    """
    Gợi ý nhập hàng dựa trên:
    - Demand: avg daily sales (sale_amount) theo ngày trong time_range gần nhất (bám MAX(dt))
    - Supply signal: inventory snapshot (lấy dòng mới nhất theo MAX(inventory_id))

    Lưu ý: sale_amount là doanh thu => suggested_replenishment là "giá trị nhập đề xuất" (budget/value),
    chưa thể là "số lượng" nếu DB không có actual_qty.
    """

    rr = _resolve_range_by_sales_max_dt(db, time_range, store_id=store_id, product_id=product_id)
    from_date = rr["from_date"]
    to_date = rr["to_date"]
    bounds = rr["bounds"]

    if from_date is None or to_date is None:
        return {
            "meta": {
                "time_range": time_range,
                "bounds": bounds,
                "page": max(int(page or 1), 1),
                "page_size": max(min(int(page_size or 100), 500), 1),
                "total_count": 0,
            },
            "data": [],
            "count": 0,
        }

    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 100), 500), 1)
    offset = (page - 1) * page_size

    # latest inventory per (store_id, product_id) để tránh 90 dòng nhân bản
    # daily_sales: sum sale_amount theo từng ngày
    base_sql = """
    WITH latest_inv AS (
      SELECT i.*
      FROM inventory i
      JOIN (
        SELECT store_id, product_id, MAX(inventory_id) AS max_id
        FROM inventory
        GROUP BY store_id, product_id
      ) x
      ON i.store_id = x.store_id
     AND i.product_id = x.product_id
     AND i.inventory_id = x.max_id
    ),
    daily_sales AS (
      SELECT
        s.store_id,
        s.product_id,
        s.dt,
        SUM(s.sale_amount) AS day_sales
      FROM sales s
      WHERE s.dt BETWEEN :from_d AND :to_d
        AND (:store_id IS NULL OR s.store_id = :store_id)
        AND (:product_id IS NULL OR s.product_id = :product_id)
      GROUP BY s.store_id, s.product_id, s.dt
    )
    SELECT
      ds.store_id,
      ds.product_id,
      AVG(ds.day_sales) AS avg_daily_sales,
      COALESCE(li.stock_hour6_22_cnt, 0) AS stock_availability,
      COALESCE(li.hours_stock_status, 0) AS stock_status_total
    FROM daily_sales ds
    LEFT JOIN latest_inv li
      ON ds.store_id = li.store_id AND ds.product_id = li.product_id
    GROUP BY ds.store_id, ds.product_id, li.stock_hour6_22_cnt, li.hours_stock_status
    """

    count_sql = f"""
    SELECT COUNT(*) AS total_count
    FROM (
      {base_sql}
    ) t
    """

    total_count_row = db.execute(
        text(count_sql),
        {
            "from_d": from_date,
            "to_d": to_date,
            "store_id": store_id,
            "product_id": product_id,
        },
    ).mappings().first()

    total_count = int((total_count_row or {}).get("total_count") or 0)

    data_sql = f"""
    {base_sql}
    ORDER BY avg_daily_sales DESC
    LIMIT :limit
    OFFSET :offset
    """

    rows = db.execute(
        text(data_sql),
        {
            "from_d": from_date,
            "to_d": to_date,
            "store_id": store_id,
            "product_id": product_id,
                        "limit": page_size,
                        "offset": offset,
        },
    ).mappings().all()

    results: List[Dict[str, Any]] = []

    for r in rows:
        avg_sales = float(r["avg_daily_sales"] or 0.0)
        stock_avail = int(r["stock_availability"] or 0)

        # Rule theo giờ bán 6–22 (16 giờ). Bạn có thể chỉnh ngưỡng để “đẹp report”
        status = "Ổn định"
        risk_level = "low"
        suggested = 0.0

        if stock_avail < 5:
            status = "Cần nhập gấp (Critical)"
            risk_level = "high"
            suggested = avg_sales * 7 * 1.5  # gợi ý budget/value cho 7 ngày * buffer
        elif stock_avail < 12:
            status = "Cần bổ sung (Warning)"
            risk_level = "medium"
            suggested = avg_sales * 7

        results.append(
            {
                "store_id": int(r["store_id"]),
                "product_id": int(r["product_id"]),
                "avg_daily_sales": round(avg_sales, 2),
                "stock_availability_hours": stock_avail,
                "status": status,
                "risk_level": risk_level,
                # value/budget đề xuất (vì sale_amount là doanh thu)
                "suggested_replenishment": round(suggested, 2),
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
            "total_count": total_count,
            "note": "suggested_replenishment is VALUE (sale_amount-based), not quantity",
        },
        "data": results,
        "count": len(results),
    }
