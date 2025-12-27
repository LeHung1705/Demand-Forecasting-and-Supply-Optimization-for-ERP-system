import os
# SỬA DÒNG NÀY: import từ pydantic_settings thay vì pydantic
from pydantic_settings import BaseSettings


_APP_DIR = os.path.abspath(os.path.dirname(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_APP_DIR, ".."))

class Settings(BaseSettings):
    APP_NAME: str = "Demand Forecasting ERP"
    API_PREFIX: str = "/api/v1"
    
    # Cấu hình CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Cấu hình đường dẫn cho DuckDB và CSV
    # Lưu ý: nếu không set env, mặc định sẽ trỏ vào file trong repo:
    # - CSV: backend/app/data/original_data.csv
    # - DuckDB cache: backend/.cache/app.duckdb
    CSV_PATH: str = os.getenv("CSV_PATH", os.path.join(_APP_DIR, "data", "original_data.csv"))
    DUCKDB_PATH: str = os.getenv("DUCKDB_PATH", os.path.join(_BACKEND_DIR, ".cache", "app.duckdb"))

    class Config:
        case_sensitive = True

settings = Settings()