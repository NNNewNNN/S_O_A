import logging

import grpc

from app.config import API_KEY

logger = logging.getLogger("auth")


def _abort_unauthenticated(request, context):
    context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing API key")


class AuthInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata or [])
        if metadata.get("x-api-key") != API_KEY:
            logger.warning(f"UNAUTHENTICATED: {handler_call_details.method}")
            return grpc.unary_unary_rpc_method_handler(_abort_unauthenticated)
        return continuation(handler_call_details)