from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import duckdb


@dataclass(frozen=True)
class Bounds:
    min_dt: Optional[str]
    max_dt: Optional[str]
    available_days: int


def _days_for_range(time_range: str) -> int:
    if time_range == "90d":
        return 90
    if time_range == "30d":
        return 30
    return 7


class CsvDuckStore:
    """
    Persistent DuckDB cache over CSV.

    - DB file: DUCKDB_PATH (backend/.cache/app.duckdb)
    - Materialized table: sales (normalized types)
    - Rebuild when CSV mtime changes.
    """

    _lock = threading.Lock()
    _instance: Optional["CsvDuckStore"] = None

    def __init__(self, csv_path: str, duckdb_path: str):
        self.csv_path = csv_path
        self.duckdb_path = duckdb_path
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    @classmethod
    def instance(cls, csv_path: str, duckdb_path: str) -> "CsvDuckStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = CsvDuckStore(csv_path=csv_path, duckdb_path=duckdb_path)
            return cls._instance

    def init(self) -> None:
        os.makedirs(os.path.dirname(self.duckdb_path), exist_ok=True)

        self._conn = duckdb.connect(self.duckdb_path)
        c = self._conn

        c.execute("CREATE TABLE IF NOT EXISTS app_meta(k VARCHAR PRIMARY KEY, v VARCHAR)")
        csv_mtime = str(int(os.path.getmtime(self.csv_path))) if os.path.exists(self.csv_path) else "0"
        cached = c.execute("SELECT v FROM app_meta WHERE k='csv_mtime'").fetchone()
        cached_mtime = cached[0] if cached else None

        # Detect if sales table exists
        exists_row = c.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='sales'"
        ).fetchone()
        sales_exists = bool((exists_row[0] or 0) > 0)

        need_rebuild = (not sales_exists) or (cached_mtime != csv_mtime)

        if need_rebuild:
            print("⏳ Đang tạo lại bảng dữ liệu DuckDB từ CSV (sẽ mất vài giây)...")
            c.execute("DROP TABLE IF EXISTS sales")

            # Create normalized "sales" table
            # LƯU Ý: Đã sửa hours_sale và hours_stock_status thành VARCHAR để tránh lỗi
            c.execute(
                """
                CREATE TABLE sales AS
                SELECT
                  CAST(city_id AS INTEGER)             AS city_id,
                  CAST(store_id AS INTEGER)            AS store_id,
                  CAST(management_group_id AS INTEGER) AS management_group_id,
                  CAST(first_category_id AS INTEGER)   AS first_category_id,
                  CAST(second_category_id AS INTEGER)  AS second_category_id,
                  CAST(third_category_id AS INTEGER)   AS third_category_id,
                  CAST(product_id AS INTEGER)          AS product_id,
                  CAST(dt AS DATE)                     AS dt,
                  CAST(sale_amount AS DOUBLE)          AS sale_amount,
                  CAST(hours_sale AS VARCHAR)          AS hours_sale, 
                  CAST(stock_hour6_22_cnt AS INTEGER)  AS stock_hour6_22_cnt,
                  CAST(hours_stock_status AS VARCHAR)  AS hours_stock_status,
                  CAST(discount AS DOUBLE)             AS discount,
                  CAST(holiday_flag AS INTEGER)        AS holiday_flag,
                  CAST(activity_flag AS INTEGER)       AS activity_flag,
                  CAST(precpt AS DOUBLE)               AS precpt,
                  CAST(avg_temperature AS DOUBLE)      AS avg_temperature,
                  CAST(avg_humidity AS DOUBLE)         AS avg_humidity,
                  CAST(avg_wind_level AS DOUBLE)       AS avg_wind_level
                FROM read_csv_auto(?, header=true)
                """,
                [self.csv_path],
            )

            c.execute("INSERT OR REPLACE INTO app_meta(k, v) VALUES ('csv_mtime', ?)", [csv_mtime])

            # Best-effort indexes
            for stmt in [
                "CREATE INDEX idx_sales_dt ON sales(dt)",
                "CREATE INDEX idx_sales_store ON sales(store_id)",
                "CREATE INDEX idx_sales_product ON sales(product_id)",
                "CREATE INDEX idx_sales_store_product ON sales(store_id, product_id)",
            ]:
                try:
                    c.execute(stmt)
                except Exception:
                    pass
            print("✅ Đã tải xong dữ liệu!")

    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            raise RuntimeError("CsvDuckStore not initialized. Call init() on startup.")
        return self._conn

    def query(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[Dict[str, Any]]:
        cur = self.conn().execute(sql, list(params) if params is not None else [])
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]

    # -----------------------
    # Common helpers
    # -----------------------
    def get_bounds(
        self,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_ids: Optional[Sequence[int]] = None,
    ) -> Bounds:
        where, args = self._where(store_id=store_id, product_id=product_id, product_ids=product_ids)
        row = self.conn().execute(
            f"""
            SELECT MIN(dt) AS min_dt, MAX(dt) AS max_dt, COUNT(DISTINCT dt) AS available_days
            FROM sales
            WHERE {where}
            """,
            args,
        ).fetchone()

        if not row or row[1] is None:
            return Bounds(min_dt=None, max_dt=None, available_days=0)

        return Bounds(
            min_dt=str(row[0]) if row[0] is not None else None,
            max_dt=str(row[1]) if row[1] is not None else None,
            available_days=int(row[2] or 0),
        )

    def resolve_time_range_by_max_dt(
        self,
        time_range: str = "30d",
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[date], Optional[date], Dict[str, Any]]:
        b = self.get_bounds(store_id=store_id, product_id=product_id, product_ids=product_ids)
        if b.max_dt is None:
            return None, None, {"min_dt": None, "max_dt": None, "available_days": 0}

        to_date = date.fromisoformat(b.max_dt)
        days = _days_for_range(time_range)
        from_date = to_date - timedelta(days=days - 1)

        if b.min_dt is not None:
            min_dt = date.fromisoformat(b.min_dt)
            if from_date < min_dt:
                from_date = min_dt

        return from_date, to_date, {"min_dt": b.min_dt, "max_dt": b.max_dt, "available_days": b.available_days}

    def aggregate_sales_by_day(
        self,
        from_date: date,
        to_date: date,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_ids: Optional[Sequence[int]] = None,
    ) -> List[Dict[str, Any]]:
        where, args = self._where(store_id=store_id, product_id=product_id, product_ids=product_ids)
        return self.query(
            f"""
            SELECT dt AS key, SUM(sale_amount) AS value
            FROM sales
            WHERE dt BETWEEN ? AND ?
              AND {where}
            GROUP BY dt
            ORDER BY dt
            """,
            [from_date, to_date, *args],
        )

    def _where(
        self,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        args: List[Any] = []

        if store_id is not None:
            clauses.append("store_id = ?")
            args.append(int(store_id))

        if product_id is not None:
            clauses.append("product_id = ?")
            args.append(int(product_id))

        if product_ids:
            placeholders = ",".join(["?"] * len(product_ids))
            clauses.append(f"product_id IN ({placeholders})")
            args.extend([int(x) for x in product_ids])

        return (" AND ".join(clauses) if clauses else "1=1"), args