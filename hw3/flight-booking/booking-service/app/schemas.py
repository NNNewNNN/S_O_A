from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class CreateBookingRequest(BaseModel):
    user_id: UUID
    flight_id: UUID
    passenger_name: str = Field(min_length=1, max_length=255)
    passenger_email: EmailStr
    seat_count: int = Field(ge=1)


class BookingResponse(BaseModel):
    id: UUID
    user_id: UUID
    flight_id: UUID
    passenger_name: str
    passenger_email: str
    seat_count: int
    total_price: float
    status: BookingStatus
    created_at: datetime


class FlightDTO(BaseModel):
    id: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    available_seats: int
    price: float
    status: str