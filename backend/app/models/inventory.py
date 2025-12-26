# app/models/inventory.py
from sqlalchemy import Column, Integer
from app.database import Base

class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True, nullable=True)
    product_id = Column(Integer, index=True, nullable=True)

    # Trạng thái tồn kho theo "giờ" (đúng với schema bạn gửi)
    hours_stock_status = Column(Integer, nullable=True)
    stock_hour6_22_cnt = Column(Integer, nullable=True)
