import os
from pydantic_settings import BaseSettings

_APP_DIR = os.path.abspath(os.path.dirname(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_APP_DIR, ".."))


class Settings(BaseSettings):
    APP_NAME: str = "Demand Forecasting ERP"
    API_PREFIX: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # CSV + DuckDB cache
    # Observed
    CSV_PATH: str = os.getenv("CSV_PATH", os.path.join(_APP_DIR, "data", "original_data.csv"))
    # Recovered
    CSV_IMPUTED_PATH: str = os.getenv("CSV_IMPUTED_PATH", os.path.join(_APP_DIR, "data", "imputed_data.csv"))

    DUCKDB_PATH: str = os.getenv("DUCKDB_PATH", os.path.join(_BACKEND_DIR, ".cache", "app.duckdb"))

    DATA_PATH: str = '/home/quang_ai/Demand-Forecasting-and-Supply-Optimization-for-ERP-system/backend/app/data'

    INFERENCE_DF_SH: str = '/home/quang_ai/Demand-Forecasting-and-Supply-Optimization-for-ERP-system/ai/demand_forecasting/inference_dlinear.sh'

    class Config:
        case_sensitive = True


settings = Settings()