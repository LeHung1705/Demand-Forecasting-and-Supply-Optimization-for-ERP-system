from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Response

from app.config import settings
from app.data.csv_store import CsvDuckStore
from app.schemas.product import ProductCreate, ProductListOut, ProductOut, ProductUpdate
from app.services.product_service import get_product, list_products

router = APIRouter(prefix="/products", tags=["products"])


def _csv_path() -> Path:
    # Keep consistent with DuckDB loader path
    return Path(settings.CSV_PATH).resolve()


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"CSV file not found: {path.as_posix()}")
    except PermissionError:
        # Common when CSV is open in Excel
        raise HTTPException(status_code=423, detail="CSV file is locked (e.g. opened in Excel). Please close it and retry.")


def _atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        df.to_csv(tmp, index=False, encoding="utf-8-sig")
        os.replace(tmp, path)
    except PermissionError:
        # Either writing temp or replacing into locked file
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=423, detail="CSV file is locked (e.g. opened in Excel). Please close it and retry.")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"CSV path not found: {path.as_posix()}")


def _norm_product_id_series(df: pd.DataFrame) -> pd.Series:
    if "product_id" not in df.columns:
        raise HTTPException(status_code=500, detail="CSV missing required column: product_id")
    return pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")


def _pick_existing_int(df: pd.DataFrame, col: str, default: int = 0) -> int:
    if col not in df.columns or df.empty:
        return default
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return default
    # Choose the most frequent to avoid introducing new store/city IDs
    mode = s.mode()
    return int(mode.iloc[0]) if not mode.empty else int(s.iloc[0])


def _pick_existing_dt_str(df: pd.DataFrame) -> str:
    if "dt" not in df.columns or df.empty:
        # Avoid extending the dataset range if possible (but if empty, nothing to preserve)
        return pd.Timestamp("1970-01-01").date().isoformat()
    s = pd.to_datetime(df["dt"], errors="coerce").dropna()
    if s.empty:
        return pd.Timestamp("1970-01-01").date().isoformat()
    # IMPORTANT: keep within existing range (use current max dt)
    return s.max().date().isoformat()


@router.get("", response_model=ProductListOut)
def api_list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    product_id: Optional[int] = None,
    first_category_id: Optional[int] = None,
    second_category_id: Optional[int] = None,
    third_category_id: Optional[int] = None,
    management_group_id: Optional[int] = None,
):
    items, total = list_products(
        page=page,
        page_size=page_size,
        product_id=product_id,
        first_category_id=first_category_id,
        second_category_id=second_category_id,
        third_category_id=third_category_id,
        management_group_id=management_group_id,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{product_id}", response_model=ProductOut)
def api_get_product(product_id: int):
    return get_product(product_id)


@router.post("", response_model=ProductOut, status_code=201)
def api_create_product(payload: ProductCreate):
    path = _csv_path()
    df = _read_csv(path)

    pid = int(payload.product_id)
    pid_series = _norm_product_id_series(df)
    if (pid_series == pid).any():
        raise HTTPException(status_code=409, detail=f"Product already exists: {pid}")

    # Create a minimal row that won't extend time bounds or introduce new store/city IDs
    new_row = {c: None for c in df.columns}

    # Common columns expected by CsvDuckStore casts (only set if present)
    if "city_id" in df.columns:
        new_row["city_id"] = _pick_existing_int(df, "city_id", default=0)
    if "store_id" in df.columns:
        new_row["store_id"] = _pick_existing_int(df, "store_id", default=0)
    if "dt" in df.columns:
        new_row["dt"] = _pick_existing_dt_str(df)

    # Product meta
    if "product_id" in df.columns:
        new_row["product_id"] = pid
    if "first_category_id" in df.columns:
        new_row["first_category_id"] = int(payload.first_category_id) if payload.first_category_id is not None else 0
    if "second_category_id" in df.columns:
        new_row["second_category_id"] = int(payload.second_category_id) if payload.second_category_id is not None else 0
    if "third_category_id" in df.columns:
        new_row["third_category_id"] = int(payload.third_category_id) if payload.third_category_id is not None else 0
    if "management_group_id" in df.columns:
        new_row["management_group_id"] = int(payload.management_group_id) if payload.management_group_id is not None else 0

    # Keep sales fields neutral
    if "sale_amount" in df.columns:
        new_row["sale_amount"] = 0.0
    if "stock_hour6_22_cnt" in df.columns:
        new_row["stock_hour6_22_cnt"] = 0
    if "discount" in df.columns:
        new_row["discount"] = 0.0
    if "holiday_flag" in df.columns:
        new_row["holiday_flag"] = 0
    if "activity_flag" in df.columns:
        new_row["activity_flag"] = 0

    # CODE CŨ (Đang bị warning):
    # df2 = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # CODE MỚI:
    # Loại bỏ các cột "trống rỗng" (all-NA) khỏi dòng mới trước khi gộp
    df2 = pd.concat([df, pd.DataFrame([new_row]).dropna(axis=1, how='all')], ignore_index=True)

    _atomic_write_csv(df2, path)

    # CRITICAL: make DuckDB see latest CSV without restart
    CsvDuckStore.instance().refresh_view()

    # Return from DuckDB-backed read path (now synced)
    return get_product(pid)


@router.put("/{product_id}", response_model=ProductOut)
def api_update_product(product_id: int, payload: ProductUpdate):
    path = _csv_path()
    df = _read_csv(path)

    pid = int(product_id)
    pid_series = _norm_product_id_series(df)
    mask = pid_series == pid
    if not bool(mask.any()):
        raise HTTPException(status_code=404, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)
    # Only apply non-None updates (None => "do not change")
    def _apply_int_col(col: str, value: Optional[int]) -> None:
        if value is None:
            return
        if col in df.columns:
            df.loc[mask, col] = int(value)

    _apply_int_col("first_category_id", updates.get("first_category_id"))
    _apply_int_col("second_category_id", updates.get("second_category_id"))
    _apply_int_col("third_category_id", updates.get("third_category_id"))
    _apply_int_col("management_group_id", updates.get("management_group_id"))

    _atomic_write_csv(df, path)

    # CRITICAL: sync DuckDB view
    CsvDuckStore.instance().refresh_view()

    return get_product(pid)


@router.delete("/{product_id}", status_code=204)
def api_delete_product(product_id: int):
    path = _csv_path()
    df = _read_csv(path)

    pid = int(product_id)
    pid_series = _norm_product_id_series(df)
    mask = pid_series == pid
    if not bool(mask.any()):
        raise HTTPException(status_code=404, detail="Product not found")

    df2 = df.loc[~mask].copy()

    _atomic_write_csv(df2, path)

    # CRITICAL: sync DuckDB view
    CsvDuckStore.instance().refresh_view()

    return Response(status_code=204)
