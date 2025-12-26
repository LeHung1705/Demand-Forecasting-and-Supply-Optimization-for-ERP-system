from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Demand Forecasting API"
    DEBUG: bool = True
    DATABASE_URL: str
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"   # file .env nằm trong thư mục backend/

settings = Settings()