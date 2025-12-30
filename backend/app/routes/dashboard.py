from __future__ import annotations
import pandas as pd

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional
import os
from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.data.csv_store import CsvDuckStore

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_store = CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH, settings.CSV_IMPUTED_PATH)
_DAYS = {"7d": 7, "30d": 30, "90d": 90}

FORECAST_DIR = settings.DATA_PATH  # trỏ đúng thư mục chứa forecast_data
INFERENCE_DF_SH = settings.INFERENCE_DF_SH


def _r2(x: Any) -> float:
    try:
        return round(float(x or 0.0), 2)
    except Exception:
        return 0.0


def _find_today_forecast_file(today: date) -> str | None:
    today_str = today.strftime("%Y%m%d")

    for fname in os.listdir(FORECAST_DIR):
        if fname.startswith("final_forecast_") and fname.endswith(".csv"):
            if today_str in fname:
                return os.path.join(FORECAST_DIR, fname)
    return None

import subprocess


def _run_forecast_job(today: date):
    subprocess.run(
        [
            "bash",
            INFERENCE_DF_SH,
            str(today.day),
            str(today.month),
            str(today.year),
            '--no_decoder',
        ],
        check=True,
    )

import numpy as np

def _parse_forecast_str(s: Any) -> np.ndarray:
    """Parses string '[1.0 2.0 ...]' into a numpy array."""
    try:
        val = str(s).strip()
        if val.startswith('[') and val.endswith(']'):
            val = val[1:-1]
        # Split by whitespace or comma
        parts = val.replace(',', ' ').split()
        return np.array([float(x) for x in parts if x], dtype=float)
    except Exception:
        return np.array([], dtype=float)

def _load_daily_forecast_from_csv(
    csv_path: str,
    store_id: int | None,
    product_id: int | None,
    base_day: date,
) -> list[dict]:
    df = pd.read_csv(csv_path)
    
    if store_id is not None:
        df = df[df["store_id"] == store_id]
    if product_id is not None:
        df = df[df["product_id"] == product_id]

    if df.empty:
        return []

    # Parse and Sum all matching rows
    total_forecast = None
    
    for val in df["daily_forecast"]:
        arr = _parse_forecast_str(val)
        if len(arr) == 0: continue
        
        if total_forecast is None:
            total_forecast = arr
        else:
            # Ensure lengths match before adding (truncate to min length if mismatch)
            min_len = min(len(total_forecast), len(arr))
            total_forecast = total_forecast[:min_len] + arr[:min_len]

    if total_forecast is None:
        return []

    return [
        {"dt": str(base_day + timedelta(days=i + 1)), "value": _r2(v)}
        for i, v in enumerate(total_forecast)
    ]


def _load_hourly_forecast_from_csv(
    csv_path: str,
    store_id: int | None,
    product_id: int | None,
    base_day: date,
) -> list[dict]:
    df = pd.read_csv(csv_path)

    if store_id is not None:
        df = df[df["store_id"] == store_id]
    if product_id is not None:
        df = df[df["product_id"] == product_id]

    if df.empty:
        return []

    # Parse and Sum all matching rows
    total_forecast = None
    row_count = 0
    
    for val in df["hourly_forecast"]:
        arr = _parse_forecast_str(val)
        if len(arr) == 0: continue
        
        row_count += 1
        if total_forecast is None:
            total_forecast = arr
        else:
            min_len = min(len(total_forecast), len(arr))
            total_forecast = total_forecast[:min_len] + arr[:min_len]

    if total_forecast is None:
        return []
    
    # Debug logging
    print(f"Hourly Forecast Aggregation: Processed {row_count} rows. Total Sum: {np.sum(total_forecast)}")
    print(f"First 5 hourly values: {total_forecast[:5]}")

    out = []
    idx = 0
    # Assuming standard 7 days horizon logic mapping (16 hours/day)
    for d in range(7):
        day = base_day + timedelta(days=d + 1)
        for h in range(16):  # 6h → 21h
            if idx >= len(total_forecast): break
            ts = datetime.combine(day, time(hour=6 + h))
            out.append({"dt": ts.isoformat(), "value": _r2(total_forecast[idx])})
            idx += 1

    return out



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

    forecast_base_day = max_dt
    forecast_file = _find_today_forecast_file(forecast_base_day)

    if forecast_file is None:
        _run_forecast_job(forecast_base_day)
        forecast_file = _find_today_forecast_file(forecast_base_day)

    if aggregation == "daily":
        observed = [{"dt": str(p["dt"]), "value": _r2(p["value"])} for p in observed_daily_rows]
        recovered = [{"dt": str(p["dt"]), "value": _r2(p["value"])} for p in recovered_daily_rows]

        forecast = _load_daily_forecast_from_csv(forecast_file, store_id, product_id, base_day=forecast_base_day)
        print(forecast)

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

    forecast_hourly = _load_hourly_forecast_from_csv(
        forecast_file,
        store_id,
        product_id,
        base_day=max_dt,
    )


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