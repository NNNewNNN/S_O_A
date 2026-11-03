import logging
import threading
import time
from enum import Enum
from typing import Optional

import grpc

from app.config import (
    API_KEY,
    CB_FAILURE_THRESHOLD,
    CB_RECOVERY_TIMEOUT,
    FLIGHT_SERVICE_HOST,
    FLIGHT_SERVICE_PORT,
    RETRY_BASE_DELAY,
    RETRY_MAX_ATTEMPTS,
)
from app.generated import flight_pb2, flight_pb2_grpc

logger = logging.getLogger("flight_client")

_RETRYABLE = {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED}


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(self, threshold: int, timeout: int):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.opened_at: Optional[float] = None
        self.state = "CLOSED"
        self._lock = threading.Lock()

    def check(self):
        with self._lock:
            if self.state == "CLOSED":
                return
            if self.state == "OPEN":
                if time.time() - self.opened_at >= self.timeout:
                    logger.info("CircuitBreaker: OPEN -> HALF_OPEN")
                    self.state = "HALF_OPEN"
                    return
                raise CircuitOpenError("Circuit is OPEN")

    def success(self):
        with self._lock:
            if self.state == "HALF_OPEN":
                logger.info("CircuitBreaker: HALF_OPEN -> CLOSED")
            self.state = "CLOSED"
            self.failures = 0

    def failure(self):
        with self._lock:
            self.failures += 1
            if self.state == "HALF_OPEN" or self.failures >= self.threshold:
                logger.info(f"CircuitBreaker: -> OPEN (failures={self.failures})")
                self.state = "OPEN"
                self.opened_at = time.time()


class _AuthMetadataInterceptor(grpc.UnaryUnaryClientInterceptor):
    def intercept_unary_unary(self, continuation, client_call_details, request):
        metadata = list(client_call_details.metadata or [])
        metadata.append(("x-api-key", API_KEY))
        new_details = _ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials,
            client_call_details.wait_for_ready,
            client_call_details.compression,
        )
        return continuation(new_details, request)


class _ClientCallDetails(grpc.ClientCallDetails):
    def __init__(self, method, timeout, metadata, credentials, wait_for_ready, compression):
        self.method = method
        self.timeout = timeout
        self.metadata = metadata
        self.credentials = credentials
        self.wait_for_ready = wait_for_ready
        self.compression = compression


class FlightServiceClient:
    def __init__(self):
        self.cb = CircuitBreaker(CB_FAILURE_THRESHOLD, CB_RECOVERY_TIMEOUT)
        channel = grpc.insecure_channel(f"{FLIGHT_SERVICE_HOST}:{FLIGHT_SERVICE_PORT}")
        channel = grpc.intercept_channel(channel, _AuthMetadataInterceptor())
        self.stub = flight_pb2_grpc.FlightServiceStub(channel)

    def _call(self, method, request):
        self.cb.check()
        last_error = None
        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            try:
                result = method(request)
                self.cb.success()
                return result
            except grpc.RpcError as e:
                last_error = e
                if e.code() not in _RETRYABLE or attempt >= RETRY_MAX_ATTEMPTS:
                    self.cb.failure()
                    raise
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    f"retry {attempt}/{RETRY_MAX_ATTEMPTS} in {delay:.2f}s ({e.code().name})"
                )
                time.sleep(delay)
        self.cb.failure()
        raise last_error

    def search_flights(self, origin, destination, date=None):
        req = flight_pb2.SearchFlightsRequest(origin=origin, destination=destination)
        if date:
            req.date.FromDatetime(date)
        return self._call(self.stub.SearchFlights, req)

    def get_flight(self, flight_id):
        return self._call(self.stub.GetFlight, flight_pb2.GetFlightRequest(id=str(flight_id)))

    def reserve_seats(self, flight_id, seat_count, booking_id):
        return self._call(
            self.stub.ReserveSeats,
            flight_pb2.ReserveSeatsRequest(
                flight_id=str(flight_id),  
                seat_count=seat_count, 
                booking_id=str(booking_id),
            ),
        )

    def release_reservation(self, booking_id):
        return self._call(
            self.stub.ReleaseReservation,
            flight_pb2.ReleaseReservationRequest(booking_id=booking_id),
        )


flight_client = FlightServiceClient()