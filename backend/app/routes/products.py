# app/routes/products.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import get_db
from app.schemas.product import ProductOut, ProductCreate, ProductUpdate, ProductListOut
from app.services.product_service import (
    list_products, get_product, create_product, update_product, delete_product
)

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=ProductListOut)
def api_list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    product_id: Optional[int] = None,
    first_category_id: Optional[int] = None,
    second_category_id: Optional[int] = None,
    third_category_id: Optional[int] = None,
    management_group_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    items, total = list_products(
        db, page, page_size,
        product_id,
        first_category_id, second_category_id, third_category_id, management_group_id
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@router.get("/{product_id}", response_model=ProductOut)
def api_get_product(product_id: int, db: Session = Depends(get_db)):
    return get_product(db, product_id)

@router.post("", response_model=ProductOut, status_code=201)
def api_create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    return create_product(db, payload)

@router.put("/{product_id}", response_model=ProductOut)
def api_update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    return update_product(db, product_id, payload)

@router.delete("/{product_id}", status_code=204)
def api_delete_product(product_id: int, db: Session = Depends(get_db)):
    delete_product(db, product_id)
    return None
