from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Response

from app.data.csv_store import CsvDuckStore
from app.schemas.product import ProductCreate, ProductListOut, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])

_MASTER_COLS = [
    "store_id",
    "product_id",
    "city_id",
    "first_category_id",
    "second_category_id",
    "third_category_id",
    "management_group_id",
]


def _csv_path() -> Path:
    # routes is backend/app/routes -> parents[1] is backend/app
    return (Path(__file__).resolve().parents[1] / "data" / "products.csv").resolve()


def _ensure_file_exists(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=_MASTER_COLS).to_csv(path, index=False)


def _read_products_df(path: Path) -> pd.DataFrame:
    _ensure_file_exists(path)
    try:
        df = pd.read_csv(path)
    except PermissionError:
        raise HTTPException(
            status_code=423,
            detail="products.csv is locked (e.g. opened in Excel). Close it and retry.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read products.csv: {e}")

    # ensure all expected columns exist (backward/forward compatible)
    for c in _MASTER_COLS:
        if c not in df.columns:
            df[c] = pd.NA

    return df[_MASTER_COLS].copy()


def _atomic_write_products(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)
    except PermissionError:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        raise HTTPException(
            status_code=423,
            detail="products.csv is locked (e.g. opened in Excel). Close it and retry.",
        )
    except Exception as e:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to write products.csv: {e}")


def _norm_int_series(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").astype("Int64")


def _list_view_df(df_master: pd.DataFrame) -> pd.DataFrame:
    """
    API is product-centric (product_id as PK). Since products.csv is keyed by
    (store_id, product_id), we aggregate by product_id for listing/get.
    """
    if df_master.empty:
        return pd.DataFrame(
            columns=[
                "product_id",
                "first_category_id",
                "second_category_id",
                "third_category_id",
                "management_group_id",
            ]
        )

    df = df_master.copy()
    df["product_id"] = _norm_int_series(df, "product_id")
    for c in ("first_category_id", "second_category_id", "third_category_id", "management_group_id"):
        df[c] = _norm_int_series(df, c)

    df = df.dropna(subset=["product_id"])
    if df.empty:
        return pd.DataFrame(
            columns=[
                "product_id",
                "first_category_id",
                "second_category_id",
                "third_category_id",
                "management_group_id",
            ]
        )

    out = (
        df.groupby("product_id", as_index=False)[
            ["first_category_id", "second_category_id", "third_category_id", "management_group_id"]
        ]
        .max()
        .sort_values("product_id")
        .reset_index(drop=True)
    )
    return out


def _to_product_out_row(r: pd.Series) -> dict:
    def _opt_int(v):
        return int(v) if pd.notna(v) else None

    return {
        "product_id": int(r["product_id"]),
        "first_category_id": _opt_int(r.get("first_category_id")),
        "second_category_id": _opt_int(r.get("second_category_id")),
        "third_category_id": _opt_int(r.get("third_category_id")),
        "management_group_id": _opt_int(r.get("management_group_id")),
    }


def _pick_existing_int(df: pd.DataFrame, col: str, default: int = 0) -> int:
    if df.empty or col not in df.columns:
        return default
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return default
    mode = s.mode()
    return int(mode.iloc[0]) if not mode.empty else int(s.iloc[0])


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
    path = _csv_path()
    df_master = _read_products_df(path)
    df = _list_view_df(df_master)

    if product_id is not None:
        df = df[df["product_id"] == int(product_id)]
    if first_category_id is not None:
        df = df[df["first_category_id"] == int(first_category_id)]
    if second_category_id is not None:
        df = df[df["second_category_id"] == int(second_category_id)]
    if third_category_id is not None:
        df = df[df["third_category_id"] == int(third_category_id)]
    if management_group_id is not None:
        df = df[df["management_group_id"] == int(management_group_id)]

    total = int(len(df))
    offset = (int(page) - 1) * int(page_size)
    df_page = df.iloc[offset : offset + int(page_size)].copy()

    return {
        "items": [_to_product_out_row(r) for _, r in df_page.iterrows()],
        "total": total,
        "page": int(page),
        "page_size": int(page_size),
    }


@router.get("/{product_id}", response_model=ProductOut)
def api_get_product(product_id: int):
    path = _csv_path()
    df_master = _read_products_df(path)
    df = _list_view_df(df_master)

    pid = int(product_id)
    hit = df[df["product_id"] == pid]
    if hit.empty:
        raise HTTPException(status_code=404, detail="Product not found")

    return _to_product_out_row(hit.iloc[0])


@router.post("", response_model=ProductOut, status_code=201)
def api_create_product(payload: ProductCreate):
    path = _csv_path()
    df = _read_products_df(path)

    pid = int(payload.product_id)
    pid_series = _norm_int_series(df, "product_id")
    if bool((pid_series == pid).any()):
        raise HTTPException(status_code=409, detail=f"Product already exists: {pid}")

    # products.csv is keyed by (store_id, product_id); create a single row.
    # Use an existing store_id/city_id to keep JOIN keys consistent for at least one store.
    new_row = {
        "store_id": _pick_existing_int(df, "store_id", default=0),
        "product_id": pid,
        "city_id": _pick_existing_int(df, "city_id", default=0),
        "first_category_id": int(payload.first_category_id) if payload.first_category_id is not None else 0,
        "second_category_id": int(payload.second_category_id) if payload.second_category_id is not None else 0,
        "third_category_id": int(payload.third_category_id) if payload.third_category_id is not None else 0,
        "management_group_id": int(payload.management_group_id) if payload.management_group_id is not None else 0,
    }

    df2 = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _atomic_write_products(df2, path)

    # CRITICAL hot reload
    CsvDuckStore.instance().refresh_view()

    return api_get_product(pid)


@router.put("/{product_id}", response_model=ProductOut)
def api_update_product(product_id: int, payload: ProductUpdate):
    path = _csv_path()
    df = _read_products_df(path)

    pid = int(product_id)
    pid_series = _norm_int_series(df, "product_id")
    mask = pid_series == pid
    if not bool(mask.any()):
        raise HTTPException(status_code=404, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)

    for col in ("first_category_id", "second_category_id", "third_category_id", "management_group_id"):
        if col in updates and updates[col] is not None:
            df.loc[mask, col] = int(updates[col])

    _atomic_write_products(df, path)

    # CRITICAL hot reload
    CsvDuckStore.instance().refresh_view()

    return api_get_product(pid)


@router.delete("/{product_id}", status_code=204)
def api_delete_product(product_id: int):
    path = _csv_path()
    df = _read_products_df(path)

    pid = int(product_id)
    pid_series = _norm_int_series(df, "product_id")
    mask = pid_series == pid
    if not bool(mask.any()):
        raise HTTPException(status_code=404, detail="Product not found")

    df2 = df.loc[~mask].copy()
    _atomic_write_products(df2, path)

    # CRITICAL hot reload
    CsvDuckStore.instance().refresh_view()

    return Response(status_code=204)
