# app/services/product_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from app.config import settings
from app.data.csv_store import CsvDuckStore
from app.schemas.product import ProductCreate, ProductUpdate


_store = CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH)


def list_products(
    page: int = 1,
    page_size: int = 20,
    product_id: Optional[int] = None,
    first_category_id: Optional[int] = None,
    second_category_id: Optional[int] = None,
    third_category_id: Optional[int] = None,
    management_group_id: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 20), 200), 1)
    offset = (page - 1) * page_size

    where = []
    args: List[Any] = []
    if product_id is not None:
        where.append("product_id = ?")
        args.append(int(product_id))
    if first_category_id is not None:
        where.append("first_category_id = ?")
        args.append(int(first_category_id))
    if second_category_id is not None:
        where.append("second_category_id = ?")
        args.append(int(second_category_id))
    if third_category_id is not None:
        where.append("third_category_id = ?")
        args.append(int(third_category_id))
    if management_group_id is not None:
        where.append("management_group_id = ?")
        args.append(int(management_group_id))

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = _store.query(
        f"""
        SELECT COUNT(*) AS n FROM (
          SELECT product_id
          FROM sales
          {where_sql}
          GROUP BY product_id
        ) t
        """,
        args,
    )[0]["n"]

    rows = _store.query(
        f"""
        SELECT
          product_id,
          MAX(first_category_id) AS first_category_id,
          MAX(second_category_id) AS second_category_id,
          MAX(third_category_id) AS third_category_id,
          MAX(management_group_id) AS management_group_id
        FROM sales
        {where_sql}
        GROUP BY product_id
        ORDER BY product_id
        LIMIT ? OFFSET ?
        """,
        [*args, page_size, offset],
    )

    items = [
        {
            "product_id": int(r["product_id"]),
            "first_category_id": int(r["first_category_id"]) if r["first_category_id"] is not None else None,
            "second_category_id": int(r["second_category_id"]) if r["second_category_id"] is not None else None,
            "third_category_id": int(r["third_category_id"]) if r["third_category_id"] is not None else None,
            "management_group_id": int(r["management_group_id"]) if r["management_group_id"] is not None else None,
        }
        for r in rows
    ]
    return items, int(total or 0)


def get_product(product_id: int) -> Dict[str, Any]:
    rows = _store.query(
        """
        SELECT
          product_id,
          MAX(first_category_id) AS first_category_id,
          MAX(second_category_id) AS second_category_id,
          MAX(third_category_id) AS third_category_id,
          MAX(management_group_id) AS management_group_id
        FROM sales
        WHERE product_id = ?
        GROUP BY product_id
        """,
        [int(product_id)],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found")

    r = rows[0]
    return {
        "product_id": int(r["product_id"]),
        "first_category_id": int(r["first_category_id"]) if r["first_category_id"] is not None else None,
        "second_category_id": int(r["second_category_id"]) if r["second_category_id"] is not None else None,
        "third_category_id": int(r["third_category_id"]) if r["third_category_id"] is not None else None,
        "management_group_id": int(r["management_group_id"]) if r["management_group_id"] is not None else None,
    }


def create_product(_payload: ProductCreate):
    raise HTTPException(status_code=501, detail="CSV mode is read-only")


def update_product(_product_id: int, _payload: ProductUpdate):
    raise HTTPException(status_code=501, detail="CSV mode is read-only")


def delete_product(_product_id: int) -> None:
    raise HTTPException(status_code=501, detail="CSV mode is read-only")
