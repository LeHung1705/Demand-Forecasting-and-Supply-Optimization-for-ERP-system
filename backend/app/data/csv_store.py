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
    _lock = threading.Lock()
    _instance: Optional["CsvDuckStore"] = None

    def __init__(self, csv_path: str, duckdb_path: str, imputed_csv_path: Optional[str] = None):
        # csv_path points to original_data.csv (transaction data)
        self.csv_path = str(csv_path or "")
        self.imputed_csv_path = str(imputed_csv_path or "")
        self.duckdb_path = str(duckdb_path or "")
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    @classmethod
    def instance(
        cls,
        csv_path: Optional[str] = None,
        duckdb_path: Optional[str] = None,
        imputed_csv_path: Optional[str] = None,
    ) -> "CsvDuckStore":
        with cls._lock:
            if cls._instance is None:
                if not csv_path or not duckdb_path:
                    raise ValueError("CsvDuckStore.instance requires csv_path and duckdb_path on first call")
                cls._instance = cls(csv_path=csv_path, duckdb_path=duckdb_path, imputed_csv_path=imputed_csv_path)
            else:
                if csv_path:
                    cls._instance.csv_path = str(csv_path)
                if duckdb_path:
                    cls._instance.duckdb_path = str(duckdb_path)
                if imputed_csv_path is not None:
                    cls._instance.imputed_csv_path = str(imputed_csv_path)
            return cls._instance

    def _drop_any(self, c: duckdb.DuckDBPyConnection, name: str) -> None:
        """
        DuckDB forbids dropping a VIEW when the object is actually a TABLE (and vice-versa).
        Previous runs may have created these names as TABLES, so always try both.
        """
        # Try view first, then table (order doesn't matter as we swallow type-mismatch errors).
        for stmt in (f"DROP VIEW IF EXISTS {name}", f"DROP TABLE IF EXISTS {name}"):
            try:
                c.execute(stmt)
            except Exception:
                pass

    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self.init()
        assert self._conn is not None
        return self._conn

    def init(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.duckdb_path)), exist_ok=True)
        self._conn = duckdb.connect(self.duckdb_path)

        c = self._conn
        c.execute("CREATE TABLE IF NOT EXISTS app_meta(k VARCHAR PRIMARY KEY, v VARCHAR)")

        # Robust cleanup for legacy TABLE/VIEW conflicts (before (re)creating anything)
        for obj in ("sales", "sales_original", "sales_imputed", "v_observed"):
            self._drop_any(c, obj)

        # Create/refresh all CSV-backed views (includes v_observed, sales_original, sales, sales_imputed)
        self.refresh_view()

    def refresh_view(self) -> None:
        """
        Master Data + Transaction Data architecture:

        - Transaction (sales): self.csv_path (original_data.csv)
        - Master (products): products.csv in the same folder as original_data.csv

        CRITICAL:
        - DuckDB CREATE VIEW cannot use `?` parameters. Use f-strings for paths.
        - v_observed is a unified view joining sales + products metadata.
        - MUST drop BOTH TABLE and VIEW variants before recreating to avoid CatalogException.
        """
        c = self._conn if self._conn is not None else duckdb.connect(self.duckdb_path)
        if self._conn is None:
            self._conn = c

        path_sales = os.path.abspath(self.csv_path)
        base_dir = os.path.dirname(path_sales)
        path_products = os.path.join(base_dir, "products.csv")

        # Inline + escape for SQL string literal
        sales_sql = path_sales.replace("\\", "/").replace("'", "''")
        products_sql = path_products.replace("\\", "/").replace("'", "''")

        # Robust cleanup for legacy TABLE/VIEW conflicts
        for obj in ("sales", "sales_original", "sales_imputed", "v_observed"):
            self._drop_any(c, obj)

        products_exists = os.path.exists(path_products)

        if products_exists:
            # Explicit projection to avoid duplicate column names (s.* + p.city_id would collide)
            c.execute(
                f"""
                CREATE OR REPLACE VIEW v_observed AS
                SELECT
                  CAST(s.store_id AS INTEGER)   AS store_id,
                  CAST(s.product_id AS INTEGER) AS product_id,
                  CAST(s.dt AS DATE)            AS dt,

                  CAST(s.sale_amount AS DOUBLE) AS sale_amount,
                  CAST(s.hours_sale AS VARCHAR) AS hours_sale,
                  CAST(s.stock_hour6_22_cnt AS INTEGER) AS stock_hour6_22_cnt,
                  CAST(s.hours_stock_status AS VARCHAR) AS hours_stock_status,
                  CAST(s.discount AS DOUBLE)    AS discount,
                  CAST(s.holiday_flag AS INTEGER) AS holiday_flag,
                  CAST(s.activity_flag AS INTEGER) AS activity_flag,
                  CAST(s.precpt AS DOUBLE)      AS precpt,
                  CAST(s.avg_temperature AS DOUBLE) AS avg_temperature,
                  CAST(s.avg_humidity AS DOUBLE) AS avg_humidity,
                  CAST(s.avg_wind_level AS DOUBLE) AS avg_wind_level,

                  -- Master data (prefer products.csv; fallback to sales columns if present)
                  CAST(COALESCE(p.city_id, s.city_id) AS INTEGER) AS city_id,
                  CAST(COALESCE(p.first_category_id, s.first_category_id) AS INTEGER) AS first_category_id,
                  CAST(COALESCE(p.second_category_id, s.second_category_id) AS INTEGER) AS second_category_id,
                  CAST(COALESCE(p.third_category_id, s.third_category_id) AS INTEGER) AS third_category_id,
                  CAST(COALESCE(p.management_group_id, s.management_group_id) AS INTEGER) AS management_group_id
                FROM read_csv_auto('{sales_sql}', header=true) s
                LEFT JOIN read_csv_auto('{products_sql}', header=true) p
                  ON CAST(s.store_id AS INTEGER) = CAST(p.store_id AS INTEGER)
                 AND CAST(s.product_id AS INTEGER) = CAST(p.product_id AS INTEGER)
                """
            )
        else:
            # Fallback: single-file mode (no products.csv yet)
            c.execute(
                f"""
                CREATE OR REPLACE VIEW v_observed AS
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
                FROM read_csv_auto('{sales_sql}', header=true)
                """
            )

        # Keep legacy names used across services/routes
        c.execute("CREATE OR REPLACE VIEW sales_original AS SELECT * FROM v_observed")
        c.execute("CREATE OR REPLACE VIEW sales AS SELECT * FROM sales_original")

        # (Re)create sales_imputed as a VIEW (never a TABLE), to avoid future conflicts.
        if self.imputed_csv_path and os.path.exists(self.imputed_csv_path):
            path_rec = os.path.abspath(self.imputed_csv_path).replace("\\", "/").replace("'", "''")
            c.execute(
                f"""
                CREATE OR REPLACE VIEW sales_imputed AS
                SELECT
                  CAST(store_id AS INTEGER)   AS store_id,
                  CAST(product_id AS INTEGER) AS product_id,
                  CAST(dt AS DATE)            AS dt,
                  CAST(sale_amount AS DOUBLE) AS sale_amount,
                  CAST(hours_sale AS VARCHAR) AS hours_sale,
                  CAST(stock_hour6_22_cnt AS INTEGER) AS stock_hour6_22_cnt,
                  CAST(hours_stock_status AS VARCHAR) AS hours_stock_status,
                  CAST(discount AS DOUBLE)    AS discount,
                  CAST(holiday_flag AS INTEGER) AS holiday_flag,
                  CAST(activity_flag AS INTEGER) AS activity_flag,
                  CAST(precpt AS DOUBLE)      AS precpt,
                  CAST(avg_temperature AS DOUBLE) AS avg_temperature,
                  CAST(avg_humidity AS DOUBLE) AS avg_humidity,
                  CAST(avg_wind_level AS DOUBLE) AS avg_wind_level
                FROM read_csv_auto('{path_rec}', header=true)
                """
            )
        else:
            c.execute("CREATE OR REPLACE VIEW sales_imputed AS SELECT * FROM sales WHERE 1=0")

        # Update mtimes (best-effort)
        try:
            if os.path.exists(path_sales):
                c.execute(
                    "INSERT OR REPLACE INTO app_meta(k, v) VALUES ('csv_mtime_original', ?)",
                    [str(int(os.path.getmtime(path_sales)))],
                )
            if products_exists:
                c.execute(
                    "INSERT OR REPLACE INTO app_meta(k, v) VALUES ('csv_mtime_products', ?)",
                    [str(int(os.path.getmtime(path_products)))],
                )
            if self.imputed_csv_path and os.path.exists(self.imputed_csv_path):
                c.execute(
                    "INSERT OR REPLACE INTO app_meta(k, v) VALUES ('csv_mtime_imputed', ?)",
                    [str(int(os.path.getmtime(self.imputed_csv_path)))],
                )
        except Exception:
            pass

    def query(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[Dict[str, Any]]:
        cur = self.conn().execute(sql, list(params or []))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

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