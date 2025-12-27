# app/services/product_service.py
from typing import Optional, Tuple, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, exists

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

def list_products(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    product_id: Optional[int] = None,
    first_category_id: Optional[int] = None,
    second_category_id: Optional[int] = None,
    third_category_id: Optional[int] = None,
    management_group_id: Optional[int] = None,
) -> Tuple[List[Product], int]:
    q = db.query(Product)

    if product_id is not None:
        q = q.filter(Product.product_id == product_id)

    if first_category_id is not None:
        q = q.filter(Product.first_category_id == first_category_id)
    if second_category_id is not None:
        q = q.filter(Product.second_category_id == second_category_id)
    if third_category_id is not None:
        q = q.filter(Product.third_category_id == third_category_id)
    if management_group_id is not None:
        q = q.filter(Product.management_group_id == management_group_id)

    total = q.count()
    items = (
        q.order_by(Product.product_id.asc())
         .offset((page - 1) * page_size)
         .limit(page_size)
         .all()
    )
    return items, total

def get_product(db: Session, product_id: int) -> Product:
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p

def create_product(db: Session, payload: ProductCreate) -> Product:
    try:
        exists_id = db.query(
            exists().where(Product.product_id == payload.product_id)
        ).scalar()

        if exists_id:
            raise HTTPException(status_code=409, detail="Product already exists")

        p = Product(**payload.model_dump())
        db.add(p)
        db.commit()
        db.refresh(p)
        return p
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Create product failed: {e}")

def update_product(db: Session, product_id: int, payload: ProductUpdate) -> Product:
    try:
        p = get_product(db, product_id)
        data = payload.model_dump(exclude_unset=True)

        # (ERP) Nếu bạn muốn chặn sửa category khi đã có sales, thêm rule ở đây.
        for k, v in data.items():
            setattr(p, k, v)

        db.commit()
        db.refresh(p)
        return p
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update product failed: {e}")

def delete_product(db: Session, product_id: int) -> None:
    """
    ERP-safe: không cho xóa nếu đã phát sinh sales hoặc inventory.
    """
    try:
        # sales check (sales có index MUL trên product_id)
        has_sales = db.execute(
            text("SELECT EXISTS(SELECT 1 FROM sales WHERE product_id = :pid LIMIT 1)"),
            {"pid": product_id},
        ).scalar()

        # inventory check (nếu có table inventory)
        has_inventory = db.execute(
            text("SELECT EXISTS(SELECT 1 FROM inventory WHERE product_id = :pid LIMIT 1)"),
            {"pid": product_id},
        ).scalar()

        if has_sales or has_inventory:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete product: referenced by sales/inventory (ERP history).",
            )

        p = get_product(db, product_id)
        db.delete(p)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete product failed: {e}")
