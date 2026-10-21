import json
import logging
import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import Message


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(record.msg, ensure_ascii=False, default=str)


logger = logging.getLogger("api.access")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False

SENSITIVE_KEYS = {"password", "refresh_token", "access_token", "token", "secret"}


def mask_sensitive(data):
    if isinstance(data, dict):
        return {
            k: ("***" if k.lower() in SENSITIVE_KEYS else mask_sensitive(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitive(item) for item in data]
    return data


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        request_body_log = None
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    parsed_body = json.loads(body_bytes)
                    request_body_log = mask_sensitive(parsed_body)
                except json.JSONDecodeError:
                    request_body_log = "<non-json>"

            async def receive() -> Message:
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            request._receive = receive

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-Id"] = request_id

        user_id = None
        user_id_from_state = getattr(request.state, "user_id", None)
        if user_id_from_state:
            user_id = str(user_id_from_state)
        else:
            auth = request.headers.get("authorization")
            if auth and auth.lower().startswith("bearer "):
                try:
                    from app.core.security import decode_access_token
                    payload = decode_access_token(auth.split(" ", 1)[1])
                    user_id = payload.get("sub")
                except Exception:
                    user_id = None

        log_record = {
            "request_id": request_id,
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if request_body_log is not None:
            log_record["request_body"] = request_body_log

        logger.info(log_record)

        return response