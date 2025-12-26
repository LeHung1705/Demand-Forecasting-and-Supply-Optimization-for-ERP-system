from sqlalchemy import Column, Integer, Date, Numeric, ForeignKey
from app.database import Base

class Sales(Base):
    __tablename__ = "sales"

    sales_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer) # Tạm thời bỏ ForeignKey để tránh lỗi nếu chưa load bảng Store
    product_id = Column(Integer) # Tạm thời bỏ ForeignKey
    dt = Column(Date, index=True)
    sale_amount = Column(Numeric(12, 2))
    hours_sale = Column(Integer)