import logging
from typing import List
from uuid import UUID, uuid4

import grpc
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.flight_client import CircuitOpenError, flight_client
from app.models import Booking, BookingStatus
from app.schemas import BookingResponse, CreateBookingRequest

logger = logging.getLogger("bookings")
router = APIRouter(prefix="/bookings", tags=["bookings"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_response(b: Booking) -> BookingResponse:
    return BookingResponse(
        id=b.id,
        user_id=b.user_id,
        flight_id=b.flight_id,
        passenger_name=b.passenger_name,
        passenger_email=b.passenger_email,
        seat_count=b.seat_count,
        total_price=float(b.total_price),
        status=b.status.value,
        created_at=b.created_at,
    )


@router.post("", response_model=BookingResponse, status_code=201)
def create_booking(payload: CreateBookingRequest, db: Session = Depends(get_db)):
    try:
        flight = flight_client.get_flight(str(payload.flight_id))
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Flight Service unavailable")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Flight not found")
        raise HTTPException(status_code=502, detail=f"GetFlight failed: {e.code().name}")

    booking_id = uuid4()

    try:
        flight_client.reserve_seats(
            flight_id=str(payload.flight_id),
            seat_count=payload.seat_count,
            booking_id=str(booking_id),
        )
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Flight Service unavailable")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
            raise HTTPException(status_code=409, detail="Not enough seats available")
        raise HTTPException(status_code=502, detail=f"ReserveSeats failed: {e.code().name}")

    total_price = flight.price * payload.seat_count
    booking = Booking(
        id=booking_id,
        user_id=payload.user_id,
        flight_id=payload.flight_id,
        passenger_name=payload.passenger_name,
        passenger_email=payload.passenger_email,
        seat_count=payload.seat_count,
        total_price=total_price,
        status=BookingStatus.CONFIRMED,
    )
    db.add(booking)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            flight_client.release_reservation(str(booking_id))
        except Exception as e:
            logger.error(f"Compensation failed for {booking_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save booking")

    db.refresh(booking)
    return _to_response(booking)


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _to_response(booking)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Only CONFIRMED bookings can be cancelled")

    try:
        flight_client.release_reservation(str(booking.id))
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Flight Service unavailable")
    except grpc.RpcError as e:
        raise HTTPException(status_code=502, detail=f"ReleaseReservation failed: {e.code().name}")

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return _to_response(booking)


@router.get("", response_model=List[BookingResponse])
def list_bookings(user_id: UUID = Query(...), db: Session = Depends(get_db)):
    bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    return [_to_response(b) for b in bookings]