from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import (
    OperationType as OperationTypeORM,
    Order,
    OrderItem,
    OrderStatus as OrderStatusORM,
    UserOperation,
)


def create_order(
    db: Session,
    user_id: UUID,
    promo_code_id: Optional[UUID],
    total_amount,
    discount_amount,
    status: OrderStatusORM,
) -> Order:
    order = Order(
        user_id=user_id,
        promo_code_id=promo_code_id,
        total_amount=total_amount,
        discount_amount=discount_amount,
        status=status,
    )
    db.add(order)
    db.flush()
    return order


def get_order_by_id(db: Session, order_id: UUID) -> Optional[Order]:
    return db.get(Order, order_id)


def get_active_order(db: Session, user_id: UUID) -> Optional[Order]:
    return (
        db.query(Order)
        .filter(
            Order.user_id == user_id,
            Order.status.in_([
                OrderStatusORM.CREATED,
                OrderStatusORM.PAYMENT_PENDING,
            ]),
        )
        .first()
    )


def create_order_item(
    db: Session,
    order_id: UUID,
    product_id: UUID,
    quantity: int,
    price_at_order,
) -> OrderItem:
    order_item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        quantity=quantity,
        price_at_order=price_at_order,
    )
    db.add(order_item)
    return order_item


def delete_order_items(db: Session, order_id: UUID) -> None:
    db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()


def create_user_operation(
    db: Session,
    user_id: UUID,
    operation_type: OperationTypeORM,
) -> UserOperation:
    operation = UserOperation(
        user_id=user_id,
        operation_type=operation_type,
    )
    db.add(operation)
    return operation


def get_last_user_operation(
    db: Session,
    user_id: UUID,
    operation_type: OperationTypeORM,
) -> Optional[UserOperation]:
    return (
        db.query(UserOperation)
        .filter(
            UserOperation.user_id == user_id,
            UserOperation.operation_type == operation_type,
        )
        .order_by(UserOperation.created_at.desc())
        .first()
    )