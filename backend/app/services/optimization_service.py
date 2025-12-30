from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.csv_store import CsvDuckStore


_store = CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH, settings.CSV_IMPUTED_PATH)


def calculate_optimal_supply(
    *,
    time_range: str = "30d",
    store_id: Optional[int] = None,
    product_ids: Optional[List[int]] = None,
    constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    constraints = constraints or {}
    budget = float(constraints.get("budget", 10_000_000_000))
    max_inventory = float(constraints.get("max_inventory", 10_000_000_000))
    lead_time = int(constraints.get("lead_time", 7))

    value_cap = min(budget, max_inventory)

    # FIX: resolve_time_range_by_max_dt returns a dict, not tuple
    resolved = _store.resolve_time_range_by_max_dt(
        time_range=time_range, store_id=store_id, product_ids=product_ids
    )
    from_date = resolved.get("from_date")
    to_date = resolved.get("to_date")

    # Fetch bounds separately
    b = _store.get_bounds(store_id=store_id, product_ids=product_ids)
    bounds = {
        "min_dt": b.min_dt,
        "max_dt": b.max_dt,
        "available_days": b.available_days
    }

    if not from_date or not to_date:
        return {
            "meta": {
                "time_range": time_range,
                "from_date": None,
                "to_date": None,
                "bounds": bounds,
                "store_id": store_id,
                "product_ids": product_ids,
                "note": "No sales data found for these filters.",
            },
            "constraints_applied": {
                "budget": budget,
                "max_inventory": max_inventory,
                "lead_time": lead_time,
                "value_cap_used": value_cap,
            },
            "total_selected_value": 0.0,
            "missed_value": 0.0,
            "items_count": 0,
            "data": [],
        }

    # WHERE
    where = []
    args: List[Any] = [from_date, to_date]
    if store_id is not None:
        where.append("store_id = ?")
        args.append(int(store_id))
    if product_ids:
        placeholders = ",".join(["?"] * len(product_ids))
        where.append(f"product_id IN ({placeholders})")
        args.extend([int(x) for x in product_ids])
    where_sql = (" AND " + " AND ".join(where)) if where else ""

    rows = _store.query(
        f"""
        WITH daily AS (
          SELECT store_id, product_id, dt, SUM(sale_amount) AS daily_value
          FROM sales
          WHERE dt BETWEEN ? AND ? {where_sql}
          GROUP BY store_id, product_id, dt
        ),
        inv AS (
          SELECT store_id, product_id,
                 COALESCE(MAX(stock_hour6_22_cnt), 0) AS stock_hours
          FROM sales
          WHERE dt BETWEEN ? AND ? {where_sql}
          GROUP BY store_id, product_id
        )
        SELECT
          d.store_id,
          d.product_id,
          AVG(d.daily_value) AS avg_daily_sales_value,
          COALESCE(i.stock_hours, 0) AS stock_availability_hours
        FROM daily d
        LEFT JOIN inv i ON i.store_id = d.store_id AND i.product_id = d.product_id
        GROUP BY d.store_id, d.product_id, i.stock_hours
        """,
        [*args, from_date, to_date, *args[2:]],
    )

    candidates: List[Dict[str, Any]] = []
    for r in rows:
        avg_daily = float(r["avg_daily_sales_value"] or 0.0)
        stock_hours = int(r["stock_availability_hours"] or 0)
        coverage_days = stock_hours / 16.0

        if stock_hours < 5:
            risk_level = "high"
            safety = 1.5
            risk_weight = 3
        elif stock_hours < 12:
            risk_level = "medium"
            safety = 1.2
            risk_weight = 2
        else:
            risk_level = "low"
            safety = 1.0
            risk_weight = 1

        base_need = avg_daily * max(0.0, (float(lead_time) - coverage_days))
        optimal_value = base_need * safety

        # deterministic priority (bigger is better)
        priority = risk_weight * 1_000_000 + avg_daily

        candidates.append(
            {
                "store_id": int(r["store_id"]),
                "product_id": int(r["product_id"]),
                "avg_daily_sales_value": round(avg_daily, 2),
                "stock_availability_hours": stock_hours,
                "coverage_days_proxy": round(coverage_days, 2),
                "risk_level": risk_level,
                "lead_time_days": lead_time,
                "optimal_order_value": round(float(optimal_value), 2),
                "priority": float(priority),
            }
        )

    candidates.sort(key=lambda x: (x["priority"], x["optimal_order_value"], x["store_id"], x["product_id"]), reverse=True)

    selected: List[Dict[str, Any]] = []
    total = 0.0
    missed = 0.0

    for item in candidates:
        need = float(item["optimal_order_value"] or 0.0)
        if need <= 0:
            continue

        if total + need <= value_cap:
            selected.append({**item, "selected_value": round(need, 2), "note": ""})
            total += need
        else:
            remaining = float(value_cap - total)
            if remaining > 0:
                selected.append({**item, "selected_value": round(remaining, 2), "note": "Cut by cap"})
                total += remaining
                missed += (need - remaining)
            else:
                missed += need
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
        "constraints_applied": {
            "budget": budget,
            "max_inventory": max_inventory,
            "lead_time": lead_time,
            "value_cap_used": value_cap,
        },
        "total_selected_value": round(total, 2),
        "missed_value": round(missed, 2),
        "items_count": len(selected),
        "data": selected,
    }