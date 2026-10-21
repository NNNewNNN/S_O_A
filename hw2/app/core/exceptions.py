from typing import Any, Optional


class ApiException(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Any] = None,
    ):
        self.message = message or self.__class__.message
        self.details = details
        super().__init__(self.message)


class ValidationFailed(ApiException):
    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


class ProductNotFound(ApiException):
    status_code = 404
    error_code = "PRODUCT_NOT_FOUND"
    message = "Product not found"


class AccessDenied(ApiException):
    status_code = 403
    error_code = "ACCESS_DENIED"
    message = "Access denied"


class Unauthorized(ApiException):
    status_code = 401
    error_code = "TOKEN_INVALID"
    message = "Unauthorized"


class TokenExpired(Unauthorized):
    error_code = "TOKEN_EXPIRED"
    message = "Access token expired"


class TokenInvalid(Unauthorized):
    error_code = "TOKEN_INVALID"
    message = "Access token invalid"


class RefreshTokenInvalid(Unauthorized):
    error_code = "REFRESH_TOKEN_INVALID"
    message = "Refresh token invalid"


class InvalidCredentials(Unauthorized):
    error_code = "INVALID_CREDENTIALS"
    message = "Invalid username or password"


class OrderNotFound(ApiException):
    status_code = 404
    error_code = "ORDER_NOT_FOUND"
    message = "Order not found"


class ProductInactive(ApiException):
    status_code = 409
    error_code = "PRODUCT_INACTIVE"
    message = "Product is not active"


class OrderLimitExceeded(ApiException):
    status_code = 429
    error_code = "ORDER_LIMIT_EXCEEDED"
    message = "Order operation rate limit exceeded"


class OrderHasActive(ApiException):
    status_code = 409
    error_code = "ORDER_HAS_ACTIVE"
    message = "User already has an active order"


class InvalidStateTransition(ApiException):
    status_code = 409
    error_code = "INVALID_STATE_TRANSITION"
    message = "Invalid order state transition"


class InsufficientStock(ApiException):
    status_code = 409
    error_code = "INSUFFICIENT_STOCK"
    message = "Insufficient stock"


class PromoCodeInvalid(ApiException):
    status_code = 422
    error_code = "PROMO_CODE_INVALID"
    message = "Promo code is invalid"


class PromoCodeMinAmount(ApiException):
    status_code = 422
    error_code = "PROMO_CODE_MIN_AMOUNT"
    message = "Order amount is below promo code minimum"


class OrderOwnershipViolation(ApiException):
    status_code = 403
    error_code = "ORDER_OWNERSHIP_VIOLATION"
    message = "Order belongs to another user"