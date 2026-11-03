from datetime import datetime
from typing import List, Optional
from uuid import UUID

import grpc
from fastapi import APIRouter, HTTPException, Query

from app.flight_client import CircuitOpenError, flight_client
from app.generated import flight_pb2
from app.schemas import FlightDTO

router = APIRouter(prefix="/flights", tags=["flights"])


def _proto_to_dto(f) -> FlightDTO:
    return FlightDTO(
        id=f.id,
        flight_number=f.flight_number,
        origin=f.origin,
        destination=f.destination,
        departure_time=f.departure_time.ToDatetime(),
        arrival_time=f.arrival_time.ToDatetime(),
        total_seats=f.total_seats,
        available_seats=f.available_seats,
        price=f.price,
        status=flight_pb2.FlightStatus.Name(f.status),
    )


@router.get("", response_model=List[FlightDTO])
def search_flights(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    date: Optional[datetime] = Query(None),
):
    try:
        resp = flight_client.search_flights(origin.upper(), destination.upper(), date)
        return [_proto_to_dto(f) for f in resp.flights]
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Flight Service unavailable")
    except grpc.RpcError as e:
        raise HTTPException(status_code=502, detail=f"Flight Service error: {e.code().name}")


@router.get("/{flight_id}", response_model=FlightDTO)
def get_flight(flight_id: UUID):
    try:
        return _proto_to_dto(flight_client.get_flight(flight_id))
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Flight Service unavailable")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Flight not found")
        raise HTTPException(status_code=502, detail=f"Flight Service error: {e.code().name}")