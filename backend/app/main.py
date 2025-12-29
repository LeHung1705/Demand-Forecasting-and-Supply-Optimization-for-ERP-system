import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data.csv_store import CsvDuckStore

# Import các router
from app.routes.analytics import router as analytics_router
from app.routes.products import router as products_router
from app.routes.planning import router as planning_router
from app.routes.optimization import router as optimization_router

# NEW routers
from app.routes.meta import router as meta_router
from app.routes.dashboard import router as dashboard_router
from app.routes.export import router as export_router

API_PREFIX = os.getenv("API_PREFIX", "/api/v1")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Demand Forecasting API",
        version=os.getenv("APP_VERSION", "0.1.0"),
    )

    # Cấu hình CORS
    raw = os.getenv(
        "ALLOWED_ORIGINS",
        settings.ALLOWED_ORIGINS
        or "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080",
    )
    origins = [o.strip() for o in raw.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _init_csv_store():
        CsvDuckStore.instance(settings.CSV_PATH, settings.DUCKDB_PATH, settings.CSV_IMPUTED_PATH).init()

    # --- ĐĂNG KÝ ROUTER ---

    # 1. Router Analytics
    analytics_prefix = getattr(analytics_router, "prefix", "") or ""
    if analytics_prefix.startswith(API_PREFIX):
        app.include_router(analytics_router)
    else:
        app.include_router(analytics_router, prefix=API_PREFIX)

    # 2. Router Products
    app.include_router(products_router, prefix=API_PREFIX)

    # 3. Router Planning
    app.include_router(planning_router, prefix=API_PREFIX)

    # 4. Router Optimization
    app.include_router(optimization_router, prefix=API_PREFIX)

    # 5. NEW: META + DASHBOARD + EXPORT
    app.include_router(meta_router, prefix=API_PREFIX)
    app.include_router(dashboard_router, prefix=API_PREFIX)
    app.include_router(export_router, prefix=API_PREFIX)

    # --- ENDPOINTS CƠ BẢN ---
    @app.get("/", tags=["health"])
    def read_root():
        return {"message": "Server ERP Demand Forecasting đang chạy ngon lành!"}

    @app.get("/healthz", tags=["health"])
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()