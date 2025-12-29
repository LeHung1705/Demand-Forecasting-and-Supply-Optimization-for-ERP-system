from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import FileResponse

from app.config import settings

router = APIRouter(prefix="/export", tags=["export"])


class ExportReportRequest(BaseModel):
    """
    Frontend may send extra keys (e.g. time_range, pipeline). We must not 422 for those.
    """
    store_id: Optional[int] = None  # null => all stores
    product_id: Optional[int] = None  # null => all products
    forecast_days: int = Field(7, ge=1, le=365)
    lead_time: int = Field(2, ge=1, le=365)  # days
    service_level: float = Field(0.95, ge=0.5, le=0.999)  # e.g. 0.95

    # Pydantic v1 compatibility
    class Config:
        extra = "ignore"


def _project_backend_dir() -> Path:
    # backend/app/routes/export.py -> parents[2] == backend/
    return Path(__file__).resolve().parents[2]


def _resolve_csv_paths() -> Tuple[Path, Path, Path]:
    """
    IMPORTANT: Use settings paths because CSVs live under backend/app/data by default.
    """
    observed_csv = Path(settings.CSV_PATH).resolve()
    recovered_csv = Path(settings.CSV_IMPUTED_PATH).resolve()
    tmp_dir = _project_backend_dir() / "tmp"
    return observed_csv, recovered_csv, tmp_dir


def _detect_sale_amount_col(df: pd.DataFrame) -> str:
    for c in ("sale_amount", "sales_amount", "sales", "value", "amount"):
        if c in df.columns:
            return c
    raise HTTPException(
        status_code=500,
        detail="CSV is missing sale amount column. Expected one of: sale_amount|sales_amount|sales|value|amount",
    )


def _detect_stockout_col(df: pd.DataFrame) -> Optional[str]:
    for c in (
        "stock_hour6_22_cnt",
        "stockout_hours",
        "stockout_hrs",
        "hours_stock_status",
        "stock_hour_cnt",
    ):
        if c in df.columns:
            return c
    return None


def _require_columns(df: pd.DataFrame, cols: Tuple[str, ...], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=500, detail=f"{name} CSV missing columns: {missing}")


def _load_csv(path: Path, name: str) -> pd.DataFrame:
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Missing required CSV file: {path.as_posix()}")

    df = pd.read_csv(path)
    _require_columns(df, ("dt", "store_id", "product_id"), name=name)

    df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    df = df.dropna(subset=["dt"])

    df["store_id"] = pd.to_numeric(df["store_id"], errors="coerce")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    df = df.dropna(subset=["store_id", "product_id"])

    df["store_id"] = df["store_id"].astype(int)
    df["product_id"] = df["product_id"].astype(int)
    return df


def _filter_df(df: pd.DataFrame, store_id: Optional[int], product_id: Optional[int]) -> pd.DataFrame:
    out = df
    if store_id is not None:
        out = out[out["store_id"] == int(store_id)]
    if product_id is not None:
        out = out[out["product_id"] == int(product_id)]
    return out


def _compute_time_range_str(df_obs: pd.DataFrame, df_rec: pd.DataFrame) -> str:
    candidates = []
    if not df_obs.empty:
        candidates.append((df_obs["dt"].min(), df_obs["dt"].max()))
    if not df_rec.empty:
        candidates.append((df_rec["dt"].min(), df_rec["dt"].max()))
    if not candidates:
        return "N/A"

    mn = min(x[0] for x in candidates)
    mx = max(x[1] for x in candidates)
    return f"{mn.date().isoformat()} to {mx.date().isoformat()}"


def _forecast_mean_last_30d(df_group: pd.DataFrame, sale_col: str) -> float:
    """
    Deterministic moving-average placeholder:
    - Use recovered data only.
    - Avg daily sales over last 30 days (inclusive) of available recovered data.
    """
    if df_group.empty:
        return 0.0

    last_dt = pd.to_datetime(df_group["dt"].max())
    start_dt = last_dt.normalize() - pd.Timedelta(days=29)
    end_dt = last_dt.normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)

    w = df_group[(df_group["dt"] >= start_dt) & (df_group["dt"] <= end_dt)]
    if w.empty:
        return 0.0

    daily = w.groupby(pd.Grouper(key="dt", freq="D"))[sale_col].sum()
    if daily.empty:
        return 0.0

    return float(daily.mean())


@router.post("/report")
def export_report(req: ExportReportRequest):
    # Log inputs for debugging (per requirement)
    print(
        "EXPORT REPORT PARAMS:",
        {
            "store_id": req.store_id,
            "product_id": req.product_id,
            "forecast_days": req.forecast_days,
            "lead_time": req.lead_time,
            "service_level": req.service_level,
        },
    )

    observed_csv, recovered_csv, tmp_dir = _resolve_csv_paths()
    os.makedirs(tmp_dir, exist_ok=True)

    # Step A: Load data from REAL CSVs (no random/mock metrics)
    df_obs = _load_csv(observed_csv, name="observed (original_data.csv)")
    df_rec = _load_csv(recovered_csv, name="recovered (imputed_data.csv)")

    sale_col_obs = _detect_sale_amount_col(df_obs)
    sale_col_rec = _detect_sale_amount_col(df_rec)
    stockout_col_obs = _detect_stockout_col(df_obs)

    # Step B: Filter
    df_obs = _filter_df(df_obs, req.store_id, req.product_id)
    df_rec = _filter_df(df_rec, req.store_id, req.product_id)

    time_range_str = _compute_time_range_str(df_obs, df_rec)

    # Step C: Aggregate historical metrics per (store_id, product_id)
    if df_obs.empty:
        obs_agg = pd.DataFrame(columns=["store_id", "product_id", "stockout_hrs", "observed_sales"]).set_index(
            ["store_id", "product_id"]
        )
    else:
        if stockout_col_obs is None:
            df_obs["_stockout_hrs"] = 0
            stock_col = "_stockout_hrs"
        else:
            df_obs[stockout_col_obs] = pd.to_numeric(df_obs[stockout_col_obs], errors="coerce").fillna(0)
            stock_col = stockout_col_obs

        df_obs[sale_col_obs] = pd.to_numeric(df_obs[sale_col_obs], errors="coerce").fillna(0)

        obs_agg = (
            df_obs.groupby(["store_id", "product_id"])
            .agg(stockout_hrs=(stock_col, "sum"), observed_sales=(sale_col_obs, "sum"))
            .astype(float)
        )

    if df_rec.empty:
        rec_agg = pd.DataFrame(columns=["store_id", "product_id", "recovered_demand"]).set_index(["store_id", "product_id"])
    else:
        df_rec[sale_col_rec] = pd.to_numeric(df_rec[sale_col_rec], errors="coerce").fillna(0)
        rec_agg = df_rec.groupby(["store_id", "product_id"]).agg(recovered_demand=(sale_col_rec, "sum")).astype(float)

    summary = obs_agg.join(rec_agg, how="outer").fillna(0).reset_index()
    summary["lost_sales"] = (summary["recovered_demand"] - summary["observed_sales"]).clip(lower=0)

    # Step D: Forecast mean (daily) from recovered last 30 days per group
    if df_rec.empty:
        summary["forecast_mean_daily"] = 0.0
    else:
        fm = (
            df_rec.groupby(["store_id", "product_id"], group_keys=False)
            .apply(lambda g: _forecast_mean_last_30d(g, sale_col=sale_col_rec))
            .rename("forecast_mean_daily")
            .reset_index()
        )
        summary = summary.merge(fm, on=["store_id", "product_id"], how="left")
        summary["forecast_mean_daily"] = summary["forecast_mean_daily"].fillna(0.0)

    # Step E: Inventory metrics (per your rule)
    summary["safety_stock"] = (summary["forecast_mean_daily"] * 0.2 * float(req.lead_time)).round().astype(int)
    summary["rop"] = (summary["forecast_mean_daily"] * float(req.lead_time) + summary["safety_stock"]).round().astype(int)

    # assume current stock = 0
    summary["suggested_order"] = summary["rop"].clip(lower=0).astype(int)
    summary["status"] = summary["suggested_order"].apply(lambda x: "Reorder" if int(x) > 0 else "Sufficient")

    # Step: Output CSV structure (exact headers)
    out = pd.DataFrame(
        {
            "Store ID": summary["store_id"].astype(int),
            "Product ID": summary["product_id"].astype(int),
            "Time Range": time_range_str,
            "Lead Time": int(req.lead_time),
            "Service Level": float(req.service_level),
            "Stockout Hrs": summary["stockout_hrs"].round(2),
            "Observed Sales": summary["observed_sales"].round(2),
            "Recovered Demand": summary["recovered_demand"].round(2),
            "Lost Sales": summary["lost_sales"].round(2),
            "Forecast Mean (Daily)": summary["forecast_mean_daily"].round(2),
            "Safety Stock": summary["safety_stock"].astype(int),
            "ROP": summary["rop"].astype(int),
            "Suggested Order": summary["suggested_order"].astype(int),
            "Status": summary["status"].astype(str),
        }
    )

    store_part = f"store_{req.store_id}" if req.store_id is not None else "store_all"
    product_part = f"product_{req.product_id}" if req.product_id is not None else "product_all"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"report-{ts}-{store_part}-{product_part}.csv"
    out_path = tmp_dir / filename

    out.to_csv(out_path, index=False, encoding="utf-8-sig")

    return FileResponse(
        path=str(out_path),
        media_type="text/csv",
        filename=filename,
    )