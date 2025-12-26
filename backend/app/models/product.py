# app/models/product.py
from sqlalchemy import Column, Integer
from app.database import Base

class Product(Base):
    __tablename__ = "product"

    product_id = Column(Integer, primary_key=True, index=True)

    first_category_id = Column(Integer, nullable=True)
    second_category_id = Column(Integer, nullable=True)
    third_category_id = Column(Integer, nullable=True)
    management_group_id = Column(Integer, nullable=True)
