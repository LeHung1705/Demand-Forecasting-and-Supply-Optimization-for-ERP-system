from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import duckdb


@dataclass
class Bounds:
    min_dt: Optional[str]
    max_dt: Optional[str]
    available_days: int


class CsvDuckStore:
    """
    Persistent DuckDB cache over CSV.

    - DB file: DUCKDB_PATH (backend/.cache/app.duckdb)
    - Materialized tables:
        - sales_original (Observed)  from CSV_PATH
        - sales_imputed  (Recovered) from CSV_IMPUTED_PATH
      Compatibility view:
        - sales := sales_original

    - Rebuild when any CSV mtime changes.
    """

    _lock = threading.Lock()
    _instance: Optional["CsvDuckStore"] = None

    def __init__(self, csv_path: str, duckdb_path: str, imputed_csv_path: Optional[str] = None):
        self.csv_path = csv_path
        self.imputed_csv_path = imputed_csv_path or ""
        self.duckdb_path = duckdb_path
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    @classmethod
    def instance(cls, csv_path: str, duckdb_path: str, imputed_csv_path: Optional[str] = None) -> "CsvDuckStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(csv_path=csv_path, duckdb_path=duckdb_path, imputed_csv_path=imputed_csv_path)
            else:
                # keep latest paths if provided later (backward compatible calls)
                if imputed_csv_path and not cls._instance.imputed_csv_path:
                    cls._instance.imputed_csv_path = imputed_csv_path
            return cls._instance

    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self.init()
        assert self._conn is not None
        return self._conn

    def _table_exists(self, name: str) -> bool:
        row = self.conn().execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name=?",
            [name],
        ).fetchone()
        return bool((row[0] or 0) > 0)

    def _create_sales_table_from_csv(self, c: duckdb.DuckDBPyConnection, table_name: str, csv_path: str) -> None:
        c.execute(f"DROP TABLE IF EXISTS {table_name}")
        c.execute(
            f"""
            CREATE TABLE {table_name} AS
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
            [csv_path],
        )

    def _drop_any(self, c: duckdb.DuckDBPyConnection, name: str) -> None:
        """
        Drop either VIEW or TABLE safely (DuckDB throws if type mismatches).
        """
        # Try drop view first
        try:
            c.execute(f"DROP VIEW IF EXISTS {name}")
        except Exception:
            pass
        # Then try drop table
        try:
            c.execute(f"DROP TABLE IF EXISTS {name}")
        except Exception:
            pass

    def init(self) -> None:
        os.makedirs(os.path.dirname(self.duckdb_path), exist_ok=True)

        self._conn = duckdb.connect(self.duckdb_path)
        c = self._conn

        c.execute("CREATE TABLE IF NOT EXISTS app_meta(k VARCHAR PRIMARY KEY, v VARCHAR)")

        original_mtime = str(int(os.path.getmtime(self.csv_path))) if os.path.exists(self.csv_path) else "0"
        imputed_mtime = str(int(os.path.getmtime(self.imputed_csv_path))) if os.path.exists(self.imputed_csv_path) else "0"

        cached_original = c.execute("SELECT v FROM app_meta WHERE k='csv_mtime_original'").fetchone()
        cached_imputed = c.execute("SELECT v FROM app_meta WHERE k='csv_mtime_imputed'").fetchone()

        cached_original_mtime = cached_original[0] if cached_original else None
        cached_imputed_mtime = cached_imputed[0] if cached_imputed else None

        need_rebuild = (
            (not self._table_exists("sales_original"))
            or (not self._table_exists("sales_imputed"))
            or (cached_original_mtime != original_mtime)
            or (cached_imputed_mtime != imputed_mtime)
        )

        if need_rebuild:
            print("⏳ Đang tạo lại bảng dữ liệu DuckDB từ CSV (Observed + Recovered)...")

            # FIX: sales đôi khi là TABLE (legacy), đôi khi là VIEW
            self._drop_any(c, "sales")
            self._drop_any(c, "sales_original")
            self._drop_any(c, "sales_imputed")

            if os.path.exists(self.csv_path):
                self._create_sales_table_from_csv(c, "sales_original", self.csv_path)
            else:
                c.execute("CREATE TABLE sales_original AS SELECT 1 AS dummy WHERE 1=0")

            if self.imputed_csv_path and os.path.exists(self.imputed_csv_path):
                self._create_sales_table_from_csv(c, "sales_imputed", self.imputed_csv_path)
            else:
                c.execute("CREATE TABLE sales_imputed AS SELECT * FROM sales_original WHERE 1=0")

            # Backward compatible name used by legacy services
            c.execute("CREATE VIEW sales AS SELECT * FROM sales_original")

            c.execute("INSERT OR REPLACE INTO app_meta(k, v) VALUES ('csv_mtime_original', ?)", [original_mtime])
            c.execute("INSERT OR REPLACE INTO app_meta(k, v) VALUES ('csv_mtime_imputed', ?)", [imputed_mtime])
            c.execute("INSERT OR REPLACE INTO app_meta(k, v) VALUES ('csv_mtime', ?)", [original_mtime])

            for stmt in [
                "CREATE INDEX IF NOT EXISTS idx_sales_original_dt ON sales_original(dt)",
                "CREATE INDEX IF NOT EXISTS idx_sales_original_store ON sales_original(store_id)",
                "CREATE INDEX IF NOT EXISTS idx_sales_original_product ON sales_original(product_id)",
                "CREATE INDEX IF NOT EXISTS idx_sales_imputed_dt ON sales_imputed(dt)",
                "CREATE INDEX IF NOT EXISTS idx_sales_imputed_store ON sales_imputed(store_id)",
                "CREATE INDEX IF NOT EXISTS idx_sales_imputed_product ON sales_imputed(product_id)",
            ]:
                try:
                    c.execute(stmt)
                except Exception:
                    pass

            print("✅ Đã tải xong dữ liệu!")

    def query(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[Dict[str, Any]]:
        cur = self.conn().execute(sql, list(params or []))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # -----------------------
    # Helpers (used by services)
    # -----------------------
    def _where(
        self,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[str, List[Any]]:
        where = ["1=1"]
        args: List[Any] = []
        if store_id is not None:
            where.append("store_id = ?")
            args.append(int(store_id))
        if product_id is not None:
            where.append("product_id = ?")
            args.append(int(product_id))
        if product_ids:
            placeholders = ",".join(["?"] * len(product_ids))
            where.append(f"product_id IN ({placeholders})")
            args.extend([int(x) for x in product_ids])
        return " AND ".join(where), args

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

        if not row:
            return Bounds(min_dt=None, max_dt=None, available_days=0)

        min_dt, max_dt, available_days = row
        return Bounds(
            min_dt=str(min_dt) if min_dt is not None else None,
            max_dt=str(max_dt) if max_dt is not None else None,
            available_days=int(available_days or 0),
        )

    def resolve_time_range_by_max_dt(
        self,
        time_range: str,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_ids: Optional[Sequence[int]] = None,
        table: str = "sales_original",
    ) -> Dict[str, Optional[str]]:
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        if time_range not in days_map:
            raise ValueError("time_range must be 7d|30d|90d")

        where, args = self._where(store_id=store_id, product_id=product_id, product_ids=product_ids)
        r = self.query(f"SELECT MAX(dt) AS max_dt FROM {table} WHERE {where}", args)
        max_dt = r[0]["max_dt"] if r else None
        if max_dt is None:
            return {"from_date": None, "to_date": None, "max_dt": None}

        to_date = max_dt if isinstance(max_dt, date) else date.fromisoformat(str(max_dt))
        from_date = to_date - timedelta(days=days_map[time_range] - 1)
        return {"from_date": str(from_date), "to_date": str(to_date), "max_dt": str(to_date)}