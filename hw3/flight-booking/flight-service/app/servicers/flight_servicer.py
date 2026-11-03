import logging
from datetime import datetime

import grpc
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import cache
from app.cache import FLIGHT_TTL, SEARCH_TTL
from app.db import SessionLocal
from app.generated import flight_pb2, flight_pb2_grpc
from app.models import Flight, FlightStatus, ReservationStatus, SeatReservation

logger = logging.getLogger("flight_servicer")


def _flight_to_dict(f: Flight) -> dict:
    return {
        "id": str(f.id),
        "flight_number": f.flight_number,
        "origin": f.origin,
        "destination": f.destination,
        "departure_time": f.departure_time.isoformat(),
        "arrival_time": f.arrival_time.isoformat(),
        "total_seats": f.total_seats,
        "available_seats": f.available_seats,
        "price": float(f.price),
        "status": f.status.value,
    }


def _dict_to_proto(d: dict) -> flight_pb2.Flight:
    proto = flight_pb2.Flight(
        id=d["id"],
        flight_number=d["flight_number"],
        origin=d["origin"],
        destination=d["destination"],
        total_seats=d["total_seats"],
        available_seats=d["available_seats"],
        price=d["price"],
        status=flight_pb2.FlightStatus.Value(d["status"]),
    )
    proto.departure_time.FromDatetime(datetime.fromisoformat(d["departure_time"]))
    proto.arrival_time.FromDatetime(datetime.fromisoformat(d["arrival_time"]))
    return proto


class FlightServiceServicer(flight_pb2_grpc.FlightServiceServicer):

    def SearchFlights(self, request, context):
        origin = request.origin.upper()
        destination = request.destination.upper()
        date_str = request.date.ToDatetime().date().isoformat() if request.date.seconds else None

        cached = cache.get(cache.search_key(origin, destination, date_str))
        if cached is not None:
            return flight_pb2.SearchFlightsResponse(flights=[_dict_to_proto(d) for d in cached])

        db: Session = SessionLocal()
        try:
            stmt = select(Flight).where(
                Flight.origin == origin,
                Flight.destination == destination,
                Flight.status == FlightStatus.SCHEDULED,
            )
            if date_str:
                date_obj = datetime.fromisoformat(date_str).date()
                stmt = stmt.where(sa.cast(Flight.departure_time, sa.Date) == date_obj)

            result = [_flight_to_dict(f) for f in db.execute(stmt).scalars().all()]
            cache.set(cache.search_key(origin, destination, date_str), result, SEARCH_TTL)
            return flight_pb2.SearchFlightsResponse(flights=[_dict_to_proto(d) for d in result])
        finally:
            db.close()

    def GetFlight(self, request, context):
        cached = cache.get(cache.flight_key(request.id))
        if cached is not None:
            return _dict_to_proto(cached)

        db: Session = SessionLocal()
        try:
            flight = db.get(Flight, request.id)
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, "Flight not found")
            data = _flight_to_dict(flight)
            cache.set(cache.flight_key(request.id), data, FLIGHT_TTL)
            return _dict_to_proto(data)
        finally:
            db.close()

    def ReserveSeats(self, request, context):
            db: Session = SessionLocal()
            try:
                existing = db.execute(
                    select(SeatReservation).where(
                        SeatReservation.booking_id == request.booking_id,
                        SeatReservation.status == ReservationStatus.ACTIVE,
                    )
                ).scalar_one_or_none()
                if existing:
                    return flight_pb2.ReserveSeatsResponse(
                        reservation_id=str(existing.id),
                        reserved_seats=existing.seat_count,
                    )

                flight = db.execute(
                    select(Flight).where(Flight.id == request.flight_id).with_for_update()
                ).scalar_one_or_none()

                if not flight:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("Flight not found")
                    return flight_pb2.ReserveSeatsResponse()

                if flight.status != FlightStatus.SCHEDULED:
                    context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                    context.set_details("Flight is not scheduled")
                    return flight_pb2.ReserveSeatsResponse()

                if flight.available_seats < request.seat_count:
                    context.set_code(grpc.StatusCode.RESOURCE_EXHAUSTED)
                    context.set_details(
                        f"Not enough seats: available={flight.available_seats}, requested={request.seat_count}"
                    )
                    return flight_pb2.ReserveSeatsResponse()

                flight.available_seats -= request.seat_count
                reservation = SeatReservation(
                    flight_id=flight.id,
                    booking_id=request.booking_id,
                    seat_count=request.seat_count,
                    status=ReservationStatus.ACTIVE,
                )
                db.add(reservation)
                
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                    context.set_details("Reservation already exists")
                    return flight_pb2.ReserveSeatsResponse()

                db.refresh(reservation)
                cache.invalidate(cache.flight_key(str(flight.id)))
                cache.invalidate_search_for(flight.origin, flight.destination)

                return flight_pb2.ReserveSeatsResponse(
                    reservation_id=str(reservation.id),
                    reserved_seats=reservation.seat_count,
                )
                
            except Exception as e:
                db.rollback()
                logger.exception("ReserveSeats failed")
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return flight_pb2.ReserveSeatsResponse()
            finally:
                db.close()

    def ReleaseReservation(self, request, context):
        db: Session = SessionLocal()
        try:
            reservation = db.execute(
                select(SeatReservation)
                .where(SeatReservation.booking_id == request.booking_id)
                .with_for_update()
            ).scalar_one_or_none()
            if not reservation:
                context.abort(grpc.StatusCode.NOT_FOUND, "Reservation not found")
            if reservation.status != ReservationStatus.ACTIVE:
                return flight_pb2.ReleaseReservationResponse(success=True)

            flight = db.execute(
                select(Flight).where(Flight.id == reservation.flight_id).with_for_update()
            ).scalar_one()

            reservation.status = ReservationStatus.RELEASED
            flight.available_seats += reservation.seat_count
            db.commit()

            cache.invalidate(cache.flight_key(str(flight.id)))
            cache.invalidate_search_for(flight.origin, flight.destination)

            return flight_pb2.ReleaseReservationResponse(success=True)
        except grpc.RpcError:
            raise
        except Exception as e:
            db.rollback()
            logger.exception("ReleaseReservation failed")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()