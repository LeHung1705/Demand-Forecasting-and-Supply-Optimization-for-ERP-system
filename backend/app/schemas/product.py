# app/schemas/product.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class ProductBase(BaseModel):
    first_category_id: Optional[int] = None
    second_category_id: Optional[int] = None
    third_category_id: Optional[int] = None
    management_group_id: Optional[int] = None

class ProductCreate(ProductBase):
    product_id: int  # PK bạn đang dùng int

class ProductUpdate(ProductBase):
    pass

class ProductOut(ProductBase):
    product_id: int
    model_config = ConfigDict(from_attributes=True)

class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    page_size: int
