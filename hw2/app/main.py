from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.error_handlers import register_error_handlers
from app.core.logging_middleware import RequestLoggingMiddleware
from app.generated.models import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTokensResponse,
    OrderCreateRequest,
    OrderResponse,
    OrderStatusChangeRequest,
    OrderUpdateRequest,
    ProductCreate,
    ProductPageResponse,
    ProductResponse,
    ProductStatus as ProductStatusDTO,
    ProductUpdate,
    PromoCodeCreateRequest,
    PromoCodeResponse,
)
from app.services import auth_service, order_service, product_service, promo_code_service
from db.models import OrderStatus as OrderStatusORM, User

app = FastAPI(
    title='Marketplace API',
    version='1.0.0',
    servers=[{'url': 'http://localhost:8080'}],
)

register_error_handlers(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)


@app.post(
    "/auth/login",
    response_model=AuthTokensResponse,
)
def login_user(
    data: AuthLoginRequest,
    db: Session = Depends(get_db),
):
    return auth_service.login(
        db=db,
        payload=data,
    )


@app.post(
    "/auth/refresh",
    response_model=AuthTokensResponse,
)
def refresh_user_token(
    data: AuthRefreshRequest,
    db: Session = Depends(get_db),
):
    return auth_service.refresh_tokens(
        db=db,
        payload=data,
    )

@app.post(
    "/auth/register",
    status_code=201,
)
def register_user(
    data: AuthRegisterRequest,
    db: Session = Depends(get_db),
):
    auth_service.register_user(
        db=db,
        payload=data,
    )

    return Response(status_code=201)


@app.post(
    "/orders",
    response_model=OrderResponse,
    status_code=201,
)
def create_order(
    data: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    return order_service.create_order(db=db, user=current_user, payload=data)



@app.get(
    "/orders/{id}",
    response_model=OrderResponse,
)
def get_order_by_id(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    return order_service.get_order(db=db, user=current_user, order_id=id)



@app.put(
    "/orders/{id}",
    response_model=OrderResponse,
)
def update_order(
    id: UUID,
    data: OrderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    return order_service.update_order(db=db, user=current_user, order_id=id, payload=data)


@app.post(
    "/orders/{id}/cancel",
    response_model=OrderResponse,
)
def cancel_order(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    return order_service.cancel_order(db=db, user=current_user, order_id=id)


@app.post(
    "/orders/{id}/status",
    response_model=OrderResponse,
)
def change_order_status(
    id: UUID,
    data: OrderStatusChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    return order_service.change_order_status(
        db=db,
        user=current_user,
        order_id=id,
        target_status=OrderStatusORM(data.status.value),
    )


@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductResponse:
    return product_service.create_product(
        db=db,
        user=current_user,
        payload=data,
    )


@app.get(
    "/products",
    response_model=ProductPageResponse,
)
def list_products(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1),
    status: Optional[ProductStatusDTO] = None,
    category: Optional[str] = Query(None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductPageResponse:
    return product_service.list_products(
        db=db,
        page=page,
        size=size,
        status=status,
        category=category,
    )

@app.get(
    "/products/{id}",
    response_model=ProductResponse,
)
def get_product_by_id(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductResponse:
    return product_service.get_product(
        db=db,
        product_id=id,
    )


@app.put(
    "/products/{id}",
    response_model=ProductResponse,
)
def update_product(
    id: UUID,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductResponse:
    return product_service.update_product(
        db=db,
        user=current_user,
        product_id=id,
        payload=data,
    )


@app.delete(
    "/products/{id}",
    status_code=204,
)
def archive_product(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product_service.archive_product(
        db=db,
        user=current_user,
        product_id=id,
    )

    return Response(status_code=204)

@app.post(
    "/promo-codes",
    response_model=PromoCodeResponse,
    status_code=201,
)
def create_promo_code(
    data: PromoCodeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromoCodeResponse:
    return promo_code_service.create_promo_code(
        db=db,
        user=current_user,
        payload=data,
    )