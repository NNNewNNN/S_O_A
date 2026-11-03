import logging
from concurrent import futures

import grpc

from app.generated import flight_pb2_grpc
from app.interceptor import AuthInterceptor
from app.servicers.flight_servicer import FlightServiceServicer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=(AuthInterceptor(),),
    )
    flight_pb2_grpc.add_FlightServiceServicer_to_server(FlightServiceServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("Flight Service gRPC started on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()