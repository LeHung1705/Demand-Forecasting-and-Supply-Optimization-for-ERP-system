from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam


def _get_sales_bounds(db: Session, store_id: Optional[int], product_ids: Optional[List[int]]) -> Dict[str, Any]:
    sql = """
    SELECT
      MIN(dt) AS min_dt,
      MAX(dt) AS max_dt,
      COUNT(DISTINCT dt) AS available_days
    FROM sales
    WHERE (:store_id IS NULL OR store_id = :store_id)
      AND (:has_products = 0 OR product_id IN :product_ids)
    """
    stmt = text(sql).bindparams(bindparam("product_ids", expanding=True))
    row = db.execute(
        stmt,
        {
            "store_id": store_id,
            "has_products": 1 if product_ids else 0,
            "product_ids": product_ids or [],
        },
    ).mappings().first()

    if not row or row["max_dt"] is None:
        return {"min_dt": None, "max_dt": None, "available_days": 0}

    return {
        "min_dt": str(row["min_dt"]),
        "max_dt": str(row["max_dt"]),
        "available_days": int(row["available_days"] or 0),
    }


def _resolve_range_by_max_dt(
    db: Session,
    time_range: str,
    store_id: Optional[int],
    product_ids: Optional[List[int]],
) -> Dict[str, Any]:
    bounds = _get_sales_bounds(db, store_id, product_ids)
    if bounds["max_dt"] is None:
        return {"from_date": None, "to_date": None, "bounds": bounds, "days": 0}

    days = 7
    if time_range == "30d":
        days = 30
    elif time_range == "90d":
        days = 90

    to_date = date.fromisoformat(bounds["max_dt"])
    from_date = to_date - timedelta(days=days - 1)

    if bounds["min_dt"] is not None:
        min_dt = date.fromisoformat(bounds["min_dt"])
        if from_date < min_dt:
            from_date = min_dt

    return {"from_date": from_date, "to_date": to_date, "bounds": bounds, "days": days}


def calculate_optimal_supply(
    db: Session,
    *,
    time_range: str = "30d",
    store_id: Optional[int] = None,
    product_ids: Optional[List[int]] = None,
    constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Optimization theo VALUE (sale_amount-based).
    """
    constraints = constraints or {}
    budget = float(constraints.get("budget", 10_000_000_000))
    max_inventory = float(constraints.get("max_inventory", 10_000_000_000))
    lead_time = int(constraints.get("lead_time", 7))

    # Resolve range by MAX(dt)
    r = _resolve_range_by_max_dt(db, time_range, store_id, product_ids)
    from_date: Optional[date] = r["from_date"]
    to_date: Optional[date] = r["to_date"]
    bounds = r["bounds"]

    if from_date is None or to_date is None:
        return {
            "meta": {
                "time_range": time_range,
                "store_id": store_id,
                "product_ids": product_ids,
                "from_date": None,
                "to_date": None,
                "bounds": bounds,
                "note": "No sales data found for these filters.",
            },
            "constraints_applied": {"budget": budget, "max_inventory": max_inventory, "lead_time": lead_time},
            "total_selected_value": 0,
            "items_count": 0,
            "data": [],
        }

    # --- SỬA LỖI TẠI ĐÂY ---
    # Thay thế {store_filter} và {product_filter} bằng logic SQL trực tiếp
    # để khớp với tham số :has_products và :product_ids được truyền bên dưới.
    sql = """
    WITH daily AS (
      SELECT
        store_id,
        product_id,
        dt,
        SUM(sale_amount) AS daily_value
      FROM sales
      WHERE dt BETWEEN :from_d AND :to_d
        AND (:store_id IS NULL OR store_id = :store_id)
        AND (:has_products = 0 OR product_id IN :product_ids)
      GROUP BY store_id, product_id, dt
    ),
    inv_latest AS (
      SELECT store_id, product_id, MAX(inventory_id) AS max_id
      FROM inventory
      GROUP BY store_id, product_id
    ),
    inv_one AS (
      SELECT i.store_id, i.product_id, i.stock_hour6_22_cnt, i.hours_stock_status
      FROM inventory i
      JOIN inv_latest x ON x.max_id = i.inventory_id
    )
    SELECT
      d.store_id,
      d.product_id,
      AVG(d.daily_value) AS avg_daily_sales_value,
      COALESCE(v.stock_hour6_22_cnt, 0) AS stock_availability_hours,
      COALESCE(v.hours_stock_status, 0) AS stock_status_total
    FROM daily d
    LEFT JOIN inv_one v
      ON v.store_id = d.store_id AND v.product_id = d.product_id
    GROUP BY d.store_id, d.product_id
    """

    # Bây giờ câu SQL đã có chứa :product_ids nên dòng bindparam này sẽ hoạt động đúng
    stmt = text(sql).bindparams(bindparam("product_ids", expanding=True))
    
    rows = db.execute(
        stmt,
        {
            "from_d": from_date,
            "to_d": to_date,
            "store_id": store_id,
            "has_products": 1 if product_ids else 0,
            "product_ids": product_ids or [],
        },
    ).mappings().all()

    # Build candidates
    candidates: List[Dict[str, Any]] = []
    for row in rows:
        avg_daily = float(row["avg_daily_sales_value"] or 0.0)
        stock_hours = int(row["stock_availability_hours"] or 0)
        coverage_days = stock_hours / 16.0

        # risk logic
        if stock_hours < 5:
            risk_level = "high"
            safety = 1.5
        elif stock_hours < 12:
            risk_level = "medium"
            safety = 1.2
        else:
            risk_level = "low"
            safety = 1.0

        base_need = avg_daily * max(0.0, (lead_time - coverage_days))
        optimal_value = base_need * safety

        priority = (3 if risk_level == "high" else 2 if risk_level == "medium" else 1) * 1_000_000 + avg_daily

        candidates.append(
            {
                "store_id": int(row["store_id"]),
                "product_id": int(row["product_id"]),
                "avg_daily_sales_value": round(avg_daily, 2),
                "stock_availability_hours": stock_hours,
                "risk_level": risk_level,
                "lead_time_days": lead_time,
                "coverage_days_proxy": round(coverage_days, 2),
                "optimal_order_value": round(optimal_value, 2),
                "priority": priority,
            }
        )

    # Sort
    candidates.sort(key=lambda x: (x["priority"], x["optimal_order_value"]), reverse=True)

    # Apply caps
    value_cap = min(budget, max_inventory)
    selected: List[Dict[str, Any]] = []
    total = 0.0
    missed_opportunity = 0.0
    
    for item in candidates:
        need = float(item["optimal_order_value"] or 0.0)
        if need <= 0:
            continue

        if total + need <= value_cap:
            selected.append({**item, "selected_value": round(need, 2), "note": ""})
            total += need
        else:
            remaining = value_cap - total
            if remaining > 0:
                selected.append({**item, "selected_value": round(remaining, 2), "note": "Cut by cap"})
                total += remaining
                missed_opportunity += (need - remaining)
            else:
                missed_opportunity += need
            break

    return {
        "meta": {
            "time_range": time_range,
            "from_date": str(from_date),
            "to_date": str(to_date),
            "bounds": bounds,
            "store_id": store_id,
            "product_ids": product_ids,
            "note": "All numbers are VALUE (sale_amount-based). Not quantity.",
        },
        "constraints_applied": {"budget": budget, "max_inventory": max_inventory, "lead_time": lead_time, "value_cap_used": value_cap},
        "total_selected_value": round(total, 2),
        "missed_value": round(missed_opportunity, 2),
        "items_count": len(selected),
        "data": selected,
    }