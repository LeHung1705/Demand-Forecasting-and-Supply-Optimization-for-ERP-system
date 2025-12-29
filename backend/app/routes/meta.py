from __future__ import annotations

from fastapi import APIRouter, Query

from app.config import settings
from app.data.csv_store import CsvDuckStore

router = APIRouter(prefix="/meta", tags=["meta"])

_store = CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH, settings.CSV_IMPUTED_PATH)


def _limit(n: int) -> int:
    try:
        n = int(n)
    except Exception:
        n = 50
    return max(1, min(n, 200))


@router.get("/stores")
def list_stores(query: str = Query("", alias="query"), limit: int = Query(50, ge=1, le=200)):
    q = (query or "").strip()
    lim = _limit(limit)

    if q:
        rows = _store.query(
            """
            SELECT DISTINCT store_id AS id
            FROM sales_original
            WHERE CAST(store_id AS VARCHAR) ILIKE ?
            ORDER BY id
            LIMIT ?
            """,
            [f"%{q}%", lim],
        )
    else:
        rows = _store.query(
            """
            SELECT DISTINCT store_id AS id
            FROM sales_original
            ORDER BY id
            LIMIT ?
            """,
            [lim],
        )

    items = [int(r["id"]) for r in rows if r.get("id") is not None]
    return {"items": items, "count": len(items)}


@router.get("/products")
def list_products(query: str = Query("", alias="query"), limit: int = Query(50, ge=1, le=200)):
    q = (query or "").strip()
    lim = _limit(limit)

    if q:
        rows = _store.query(
            """
            SELECT DISTINCT product_id AS id
            FROM sales_original
            WHERE CAST(product_id AS VARCHAR) ILIKE ?
            ORDER BY id
            LIMIT ?
            """,
            [f"%{q}%", lim],
        )
    else:
        rows = _store.query(
            """
            SELECT DISTINCT product_id AS id
            FROM sales_original
            ORDER BY id
            LIMIT ?
            """,
            [lim],
        )

    items = [int(r["id"]) for r in rows if r.get("id") is not None]
    return {"items": items, "count": len(items)}