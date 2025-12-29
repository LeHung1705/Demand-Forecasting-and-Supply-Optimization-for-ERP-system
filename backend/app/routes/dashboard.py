from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.data.csv_store import CsvDuckStore

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_store = CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH, settings.CSV_IMPUTED_PATH)
_DAYS = {"7d": 7, "30d": 30, "90d": 90}


def _r2(x: Any) -> float:
    try:
        return round(float(x or 0.0), 2)
    except Exception:
        return 0.0


def _daily_sum(
    table: str,
    from_date: date,
    to_date: date,
    store_id: Optional[int],
    product_id: Optional[int],
) -> List[Dict[str, Any]]:
    where = ["dt BETWEEN ? AND ?"]
    args: List[Any] = [from_date, to_date]

    if store_id is not None:
        where.append("store_id = ?")
        args.append(int(store_id))

    if product_id is not None:
        where.append("product_id = ?")
        args.append(int(product_id))

    return _store.query(
        f"""
        SELECT dt, COALESCE(SUM(sale_amount), 0) AS value
        FROM {table}
        WHERE {" AND ".join(where)}
        GROUP BY dt
        ORDER BY dt
        """,
        args,
    )


def _expand_daily_to_hourly(daily_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fallback hourly mode: expand each daily point into 24 hourly points.
    - dt output: ISO 'YYYY-MM-DDTHH:00:00'
    - value per hour: daily_total / 24 (rounded to 2 decimals to avoid long floats)
    """
    out: List[Dict[str, Any]] = []
    for r in daily_rows:
        d = r.get("dt")
        if d is None:
            continue
        day = d if isinstance(d, date) else date.fromisoformat(str(d))
        day_total = float(r.get("value") or 0.0)
        per_hour = _r2(day_total / 24.0)

        for h in range(24):
            ts = datetime.combine(day, time(hour=h))
            out.append({"dt": ts.isoformat(), "value": per_hour})
    return out


def _dummy_forecast_daily(observed: List[Dict[str, Any]], last_day: date, horizon_days: int = 7) -> List[Dict[str, Any]]:
    tail = observed[-7:] if observed else []
    vals = [float(p.get("value") or 0.0) for p in tail]
    base = (sum(vals) / len(vals)) if vals else 0.0
    base = _r2(base)

    return [{"dt": str(last_day + timedelta(days=i)), "value": base} for i in range(1, horizon_days + 1)]


def _dummy_forecast_hourly(
    observed: List[Dict[str, Any]],
    last_ts: datetime,
    horizon_days: int = 7,
) -> List[Dict[str, Any]]:
    horizon_points = horizon_days * 24

    tail = observed[-24:] if observed else []
    vals = [float(p.get("value") or 0.0) for p in tail]
    base = (sum(vals) / len(vals)) if vals else 0.0
    base = _r2(base)

    out: List[Dict[str, Any]] = []
    for i in range(1, horizon_points + 1):
        ts = last_ts + timedelta(hours=i)
        out.append({"dt": ts.isoformat(), "value": base})
    return out


@router.get("/series")
def get_dashboard_series(
    time_range: str = Query("30d", pattern="^(7d|30d|90d)$"),
    aggregation: str = Query("daily", pattern="^(daily|hourly)$"),
    store_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
):
    if time_range not in _DAYS:
        raise HTTPException(status_code=422, detail="time_range must be 7d|30d|90d")
    if aggregation not in ("daily", "hourly"):
        raise HTTPException(status_code=422, detail="aggregation must be daily|hourly")

    where = ["1=1"]
    args: List[Any] = []
    if store_id is not None:
        where.append("store_id = ?")
        args.append(int(store_id))
    if product_id is not None:
        where.append("product_id = ?")
        args.append(int(product_id))

    r = _store.query(f"SELECT MAX(dt) AS max_dt FROM sales_original WHERE {' AND '.join(where)}", args)
    max_dt_raw = r[0]["max_dt"] if r else None

    if max_dt_raw is None:
        return {
            "meta": {
                "time_range": time_range,
                "aggregation": aggregation,
                "from_date": None,
                "to_date": None,
                "max_dt": None,
                "forecast_horizon_days": 7,
                "store_id": store_id,
                "product_id": product_id,
            },
            "observed": [],
            "recovered": [],
            "forecast": [],
        }

    max_dt = max_dt_raw if isinstance(max_dt_raw, date) else date.fromisoformat(str(max_dt_raw))
    to_date = max_dt
    from_date = to_date - timedelta(days=_DAYS[time_range] - 1)

    observed_daily_rows = _daily_sum("sales_original", from_date, to_date, store_id, product_id)
    recovered_daily_rows = _daily_sum("sales_imputed", from_date, to_date, store_id, product_id)

    if aggregation == "daily":
        observed = [{"dt": str(p["dt"]), "value": _r2(p["value"])} for p in observed_daily_rows]
        recovered = [{"dt": str(p["dt"]), "value": _r2(p["value"])} for p in recovered_daily_rows]
        forecast = _dummy_forecast_daily(observed, last_day=to_date, horizon_days=7)

        return {
            "meta": {
                "time_range": time_range,
                "aggregation": aggregation,
                "from_date": str(from_date),
                "to_date": str(to_date),
                "max_dt": str(max_dt),
                "forecast_horizon_days": 7,
                "store_id": store_id,
                "product_id": product_id,
            },
            "observed": observed,
            "recovered": recovered,
            "forecast": forecast,
        }

    observed_hourly_rows = _expand_daily_to_hourly(
        [{"dt": p["dt"], "value": _r2(p["value"])} for p in observed_daily_rows]
    )
    recovered_hourly_rows = _expand_daily_to_hourly(
        [{"dt": p["dt"], "value": _r2(p["value"])} for p in recovered_daily_rows]
    )

    if observed_hourly_rows:
        last_hist_ts = datetime.fromisoformat(str(observed_hourly_rows[-1]["dt"]))
    else:
        last_hist_ts = datetime.combine(to_date, time(hour=23))

    forecast_hourly = _dummy_forecast_hourly(observed_hourly_rows, last_ts=last_hist_ts, horizon_days=7)

    return {
        "meta": {
            "time_range": time_range,
            "aggregation": aggregation,
            "from_date": str(from_date),
            "to_date": str(to_date),
            "max_dt": str(max_dt),
            "forecast_horizon_days": 7,
            "store_id": store_id,
            "product_id": product_id,
        },
        "observed": [{"dt": str(p["dt"]), "value": _r2(p["value"])} for p in observed_hourly_rows],
        "recovered": [{"dt": str(p["dt"]), "value": _r2(p["value"])} for p in recovered_hourly_rows],
        "forecast": [{"dt": str(p["dt"]), "value": _r2(p["value"])} for p in forecast_hourly],
    }