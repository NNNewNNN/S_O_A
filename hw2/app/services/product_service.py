from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud import product as product_crud
from app.core.exceptions import AccessDenied, ProductNotFound
from app.generated.models import (
    ProductCreate,
    ProductPageResponse,
    ProductResponse,
    ProductStatus as ProductStatusDTO,
    ProductUpdate,
)
from db.models import Product, Role, User


def _to_response(product: Product) -> ProductResponse:
    status_value = getattr(product.status, "value", product.status)

    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        category=product.category,
        status=ProductStatusDTO(status_value),
        seller_id=product.seller_id,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _assert_can_create_product(user: User) -> None:
    if user.role in {Role.SELLER, Role.ADMIN}:
        return

    raise AccessDenied()


def _assert_can_manage_product(
    user: User,
    product: Product,
) -> None:
    if user.role == Role.ADMIN:
        return

    if user.role == Role.SELLER and product.seller_id == user.id:
        return

    raise AccessDenied()


def create_product(
    db: Session,
    user: User,
    payload: ProductCreate,
) -> ProductResponse:
    _assert_can_create_product(user)

    product = product_crud.create_product(
        db=db,
        payload=payload,
        seller_id=user.id,
    )

    return _to_response(product)


def get_product(
    db: Session,
    product_id: UUID,
) -> ProductResponse:
    product = product_crud.get_product_by_id(db, product_id)

    if product is None:
        raise ProductNotFound()

    return _to_response(product)


def list_products(
    db: Session,
    page: int,
    size: int,
    status: Optional[ProductStatusDTO] = None,
    category: Optional[str] = None,
) -> ProductPageResponse:
    page = max(page, 0)
    size = max(size, 1)

    items, total = product_crud.list_products(
        db=db,
        page=page,
        size=size,
        status=status,
        category=category,
    )

    content = [_to_response(item) for item in items]

    return ProductPageResponse(
        content=content,
        totalElements=total,
        page=page,
        size=size,
    )


def update_product(
    db: Session,
    user: User,
    product_id: UUID,
    payload: ProductUpdate,
) -> ProductResponse:
    product = product_crud.get_product_by_id(db, product_id)

    if product is None:
        raise ProductNotFound()

    _assert_can_manage_product(user, product)

    updated_product = product_crud.update_product(
        db=db,
        product=product,
        payload=payload,
    )

    return _to_response(updated_product)


def archive_product(
    db: Session,
    user: User,
    product_id: UUID,
) -> None:
    product = product_crud.get_product_by_id(db, product_id)

    if product is None:
        raise ProductNotFound()

    _assert_can_manage_product(user, product)

    product_crud.archive_product(
        db=db,
        product=product,
    )