import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class FlightStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    DEPARTED = "DEPARTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class Flight(Base):
    __tablename__ = "flights"
    __table_args__ = (
        CheckConstraint("total_seats > 0", name="ck_total_seats_positive"),
        CheckConstraint("available_seats >= 0", name="ck_available_seats_non_negative"),
        CheckConstraint("price > 0", name="ck_price_positive"),
        CheckConstraint("arrival_time > departure_time", name="ck_arrival_after_departure"),
        UniqueConstraint("flight_number", "departure_time", name="uq_flight_number_date"),
        Index("ix_flights_route_date", "origin", "destination", "departure_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_number: Mapped[str] = mapped_column(String(10), nullable=False)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[FlightStatus] = mapped_column(
        SAEnum(FlightStatus), default=FlightStatus.SCHEDULED, nullable=False
    )

    reservations: Mapped[list["SeatReservation"]] = relationship(back_populates="flight")


class SeatReservation(Base):
    __tablename__ = "seat_reservations"
    __table_args__ = (
        CheckConstraint("seat_count > 0", name="ck_seat_count_positive"),
        Index("ix_reservations_booking_id", "booking_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False
    )
    booking_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    seat_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus), default=ReservationStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    flight: Mapped["Flight"] = relationship(back_populates="reservations")