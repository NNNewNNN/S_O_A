from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import ApiException


def register_error_handlers(app):
    @app.exception_handler(ApiException)
    async def api_exception_handler(
        request: Request,
        exc: ApiException,
    ):
        content = {
            "error_code": exc.error_code,
            "message": exc.message,
        }

        if exc.details is not None:
            content["details"] = exc.details

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        fields = []

        for err in exc.errors():
            loc = err.get("loc", [])

            field = ".".join(
                str(part)
                for part in loc
                if part not in {"body", "query", "path", "header", "cookie"}
            )

            fields.append(
                {
                    "field": field,
                    "message": err.get("msg"),
                    "type": err.get("type"),
                }
            )

        return JSONResponse(
            status_code=400,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": {
                    "fields": fields,
                },
            },
        )