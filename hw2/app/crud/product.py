from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.generated.models import ProductCreate, ProductUpdate
from db.models import Product, ProductStatus as ProductStatusORM


def _to_orm_status(status: Any) -> ProductStatusORM:
    if status is None:
        return ProductStatusORM.ACTIVE

    if isinstance(status, ProductStatusORM):
        return status

    return ProductStatusORM(getattr(status, "value", str(status)))


def create_product(
    db: Session,
    payload: ProductCreate,
    seller_id: UUID,
) -> Product:
    product = Product(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        stock=payload.stock,
        category=payload.category,
        status=_to_orm_status(payload.status),
        seller_id=seller_id,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def get_product_by_id(
    db: Session,
    product_id: UUID,
) -> Optional[Product]:
    return db.get(Product, product_id)


def list_products(
    db: Session,
    page: int,
    size: int,
    status: Optional[Any] = None,
    category: Optional[str] = None,
) -> Tuple[List[Product], int]:
    query = db.query(Product)

    if status is not None:
        query = query.filter(Product.status == _to_orm_status(status))

    if category:
        query = query.filter(Product.category == category)

    total = query.count()

    items = (
        query
        .order_by(Product.created_at.desc())
        .offset(page * size)
        .limit(size)
        .all()
    )

    return items, total


def update_product(
    db: Session,
    product: Product,
    payload: ProductUpdate,
) -> Product:
    product.name = payload.name
    product.description = payload.description
    product.price = payload.price
    product.stock = payload.stock
    product.category = payload.category

    if payload.status is not None:
        product.status = _to_orm_status(payload.status)

    db.commit()
    db.refresh(product)

    return product


def archive_product(
    db: Session,
    product: Product,
) -> None:
    product.status = ProductStatusORM.ARCHIVED
    db.commit()