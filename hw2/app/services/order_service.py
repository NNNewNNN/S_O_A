import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccessDenied,
    InsufficientStock,
    InvalidStateTransition,
    OrderHasActive,
    OrderLimitExceeded,
    OrderNotFound,
    OrderOwnershipViolation,
    ProductInactive,
    ProductNotFound,
    PromoCodeInvalid,
    PromoCodeMinAmount,
)
from app.crud import order as order_crud
from app.crud import promo_code as promo_code_crud
from app.generated.models import (
    OrderCreateRequest,
    OrderItemResponse,
    OrderResponse,
    OrderUpdateRequest,
)
from app.services import promo_code_service
from db.models import (
    OperationType as OperationTypeORM,
    Order,
    OrderItem,
    OrderStatus as OrderStatusORM,
    Product,
    ProductStatus as ProductStatusORM,
    PromoCode,
    Role,
    User,
)

ORDER_RATE_LIMIT_MINUTES = int(os.getenv("ORDER_RATE_LIMIT_MINUTES", "1"))


ALLOWED_TRANSITIONS = {
    OrderStatusORM.CREATED: {
        OrderStatusORM.PAYMENT_PENDING,
        OrderStatusORM.CANCELED,
    },
    OrderStatusORM.PAYMENT_PENDING: {
        OrderStatusORM.PAID,
        OrderStatusORM.CANCELED,
    },
    OrderStatusORM.PAID: {
        OrderStatusORM.SHIPPED,
    },
    OrderStatusORM.SHIPPED: {
        OrderStatusORM.COMPLETED,
    },
    OrderStatusORM.COMPLETED: set(),
    OrderStatusORM.CANCELED: set(),
}


def assert_transition_allowed(
    current: OrderStatusORM,
    target: OrderStatusORM,
) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            message=(
                f"Transition from {getattr(current, 'value', current)} "
                f"to {getattr(target, 'value', target)} is not allowed"
            ),
            details={
                "current_status": getattr(current, "value", str(current)),
                "target_status": getattr(target, "value", str(target)),
            },
        )














def _assert_can_create_order(user: User) -> None:
    if user.role == Role.SELLER:
        raise AccessDenied()


def _assert_can_view_order(user: User, order: Order) -> None:
    if user.role == Role.SELLER:
        raise AccessDenied()
    if user.role == Role.ADMIN:
        return
    if order.user_id != user.id:
        raise OrderOwnershipViolation()


def _assert_can_manage_order(user: User, order: Order) -> None:
    if user.role == Role.SELLER:
        raise AccessDenied()
    if user.role == Role.ADMIN:
        return
    if order.user_id != user.id:
        raise OrderOwnershipViolation()


def _check_rate_limit(
    db: Session,
    user: User,
    operation_type: OperationTypeORM,
) -> None:
    last_op = order_crud.get_last_user_operation(
        db=db,
        user_id=user.id,
        operation_type=operation_type,
    )

    if last_op is None:
        return

    now = datetime.now(timezone.utc)
    diff = now - last_op.created_at

    if diff < timedelta(minutes=ORDER_RATE_LIMIT_MINUTES):
        raise OrderLimitExceeded()


def _check_active_order(db: Session, user: User) -> None:
    active_order = order_crud.get_active_order(db=db, user_id=user.id)
    if active_order is not None:
        raise OrderHasActive()


def _validate_products_and_stock(
    db: Session,
    items: List,
) -> List[Tuple[Product, int]]:
    product_quantities = []
    insufficient = []

    sorted_items = sorted(items, key=lambda x: str(x.product_id))

    for item in sorted_items:
        product_id = item.product_id
        quantity = item.quantity

        product = (
            db.query(Product)
            .filter(Product.id == product_id)
            .with_for_update()
            .first()
        )

        if product is None:
            raise ProductNotFound(
                details={"product_id": str(product_id)}
            )

        if product.status != ProductStatusORM.ACTIVE:
            raise ProductInactive(
                details={"product_id": str(product_id)}
            )

        if product.stock < quantity:
            insufficient.append({
                "product_id": str(product_id),
                "requested_quantity": quantity,
                "available_stock": product.stock,
            })

        product_quantities.append((product, quantity))

    if insufficient:
        raise InsufficientStock(details={"items": insufficient})

    return product_quantities


def _reserve_stock(product_quantities: List[Tuple[Product, int]]) -> None:
    for product, quantity in product_quantities:
        product.stock -= quantity


def _return_stock(db: Session, order_items: List[OrderItem]) -> None:
    sorted_items = sorted(order_items, key=lambda x: str(x.product_id))

    for order_item in sorted_items:
        product = (
            db.query(Product)
            .filter(Product.id == order_item.product_id)
            .with_for_update()
            .first()
        )
        if product is not None:
            product.stock += order_item.quantity


def _calculate_total(
    product_quantities: List[Tuple[Product, int]],
) -> Tuple[Decimal, List[Tuple[Product, int, Decimal]]]:
    total = Decimal("0")
    items_with_price = []

    for product, quantity in product_quantities:
        price_at_order = product.price
        total += price_at_order * Decimal(quantity)
        items_with_price.append((product, quantity, price_at_order))

    return total, items_with_price


def _apply_promo_code(
    db: Session,
    promo_code_str: Optional[str],
    total_amount: Decimal,
) -> Tuple[Optional[PromoCode], Decimal]:
    if not promo_code_str:
        return None, Decimal("0")

    return promo_code_service.validate_and_apply_promo_code(
        db=db,
        promo_code_str=promo_code_str,
        total_amount=total_amount,
    )



def change_order_status(
    db: Session,
    user: User,
    order_id: UUID,
    target_status: OrderStatusORM,
) -> OrderResponse:
    order = order_crud.get_order_by_id(db=db, order_id=order_id)

    if order is None:
        raise OrderNotFound()

    _assert_can_manage_order(user=user, order=order)

    assert_transition_allowed(current=order.status, target=target_status)

    try:
        if target_status == OrderStatusORM.CANCELED:
            _return_stock(db=db, order_items=list(order.items))

            if order.promo_code_id is not None:
                promo_code = promo_code_crud.get_by_id(
                    db=db, promo_code_id=order.promo_code_id,
                )
                if promo_code:
                    promo_code_crud.decrement_uses(db=db, promo_code=promo_code)

        order.status = target_status

        db.commit()
        db.refresh(order)

        return _to_response(order)

    except Exception:
        db.rollback()
        raise



def _to_response(order: Order) -> OrderResponse:
    status_value = getattr(order.status, "value", order.status)

    items = [
        OrderItemResponse(
            id=order_item.id,
            product_id=order_item.product_id,
            quantity=order_item.quantity,
            price_at_order=order_item.price_at_order,
        )
        for order_item in order.items
    ]

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=status_value,
        promo_code_id=order.promo_code_id,
        items=items,
        total_amount=order.total_amount,
        discount_amount=order.discount_amount,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def create_order(
    db: Session,
    user: User,
    payload: OrderCreateRequest,
) -> OrderResponse:
    _assert_can_create_order(user)

    _check_rate_limit(
        db=db,
        user=user,
        operation_type=OperationTypeORM.CREATE_ORDER,
    )

    _check_active_order(db=db, user=user)

    try:
        product_quantities = _validate_products_and_stock(
            db=db, items=payload.items,
        )

        _reserve_stock(product_quantities)

        total_amount, items_with_price = _calculate_total(product_quantities)

        promo_code, discount_amount = _apply_promo_code(
            db=db,
            promo_code_str=getattr(payload, "promo_code", None),
            total_amount=total_amount,
        )

        final_total = total_amount - discount_amount

        order = order_crud.create_order(
            db=db,
            user_id=user.id,
            promo_code_id=promo_code.id if promo_code else None,
            total_amount=final_total,
            discount_amount=discount_amount,
            status=OrderStatusORM.CREATED,
        )

        for product, quantity, price_at_order in items_with_price:
            order_crud.create_order_item(
                db=db,
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price_at_order=price_at_order,
            )

        if promo_code:
            promo_code_crud.increment_uses(db=db, promo_code=promo_code)

        order_crud.create_user_operation(
            db=db,
            user_id=user.id,
            operation_type=OperationTypeORM.CREATE_ORDER,
        )

        db.commit()
        db.refresh(order)

        return _to_response(order)

    except Exception:
        db.rollback()
        raise


def get_order(
    db: Session,
    user: User,
    order_id: UUID,
) -> OrderResponse:
    order = order_crud.get_order_by_id(db=db, order_id=order_id)

    if order is None:
        raise OrderNotFound()

    _assert_can_view_order(user=user, order=order)

    return _to_response(order)


def update_order(
    db: Session,
    user: User,
    order_id: UUID,
    payload: OrderUpdateRequest,
) -> OrderResponse:
    order = order_crud.get_order_by_id(db=db, order_id=order_id)

    if order is None:
        raise OrderNotFound()

    _assert_can_manage_order(user=user, order=order)

    if order.status != OrderStatusORM.CREATED:
        raise InvalidStateTransition()

    _check_rate_limit(
        db=db,
        user=user,
        operation_type=OperationTypeORM.UPDATE_ORDER,
    )

    try:
        _return_stock(db=db, order_items=list(order.items))

        order_crud.delete_order_items(db=db, order_id=order.id)
        db.flush()

        product_quantities = _validate_products_and_stock(
            db=db, items=payload.items,
        )

        _reserve_stock(product_quantities)

        total_amount, items_with_price = _calculate_total(product_quantities)

        promo_code = None
        discount_amount = Decimal("0")

        if order.promo_code_id is not None:
            promo_code = promo_code_crud.get_by_id(
                db=db, promo_code_id=order.promo_code_id,
            )

            if promo_code:
                promo_code_crud.decrement_uses(db=db, promo_code=promo_code)

                try:
                    _, discount_amount = promo_code_service.validate_and_apply_promo_code(
                        db=db,
                        promo_code_str=promo_code.code,
                        total_amount=total_amount,
                    )
                    promo_code_crud.increment_uses(db=db, promo_code=promo_code)
                except (PromoCodeInvalid, PromoCodeMinAmount):
                    promo_code = None
                    discount_amount = Decimal("0")

        final_total = total_amount - discount_amount

        order.total_amount = final_total
        order.discount_amount = discount_amount
        order.promo_code_id = promo_code.id if promo_code else None

        for product, quantity, price_at_order in items_with_price:
            order_crud.create_order_item(
                db=db,
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price_at_order=price_at_order,
            )

        order_crud.create_user_operation(
            db=db,
            user_id=user.id,
            operation_type=OperationTypeORM.UPDATE_ORDER,
        )

        db.commit()
        db.refresh(order)

        return _to_response(order)

    except Exception:
        db.rollback()
        raise


def cancel_order(
    db: Session,
    user: User,
    order_id: UUID,
) -> OrderResponse:
    order = order_crud.get_order_by_id(db=db, order_id=order_id)

    if order is None:
        raise OrderNotFound()

    _assert_can_manage_order(user=user, order=order)

    assert_transition_allowed(
    current=order.status,
    target=OrderStatusORM.CANCELED,
    )

    try:
        _return_stock(db=db, order_items=list(order.items))

        if order.promo_code_id is not None:
            promo_code = promo_code_crud.get_by_id(
                db=db, promo_code_id=order.promo_code_id,
            )

            if promo_code:
                promo_code_crud.decrement_uses(db=db, promo_code=promo_code)

        order.status = OrderStatusORM.CANCELED

        db.commit()
        db.refresh(order)

        return _to_response(order)

    except Exception:
        db.rollback()
        raise