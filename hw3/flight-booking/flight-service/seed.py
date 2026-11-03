import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.db import SessionLocal
from app.models import Flight, FlightStatus


def seed():
    db = SessionLocal()
    try:
        if db.query(Flight).count() > 0:
            print("Flights already seeded")
            return

        now = datetime.now(timezone.utc)
        flights = [
            Flight(
                id=uuid.uuid4(),
                flight_number="SU1234",
                origin="SVO",
                destination="LED",
                departure_time=now + timedelta(days=7, hours=8),
                arrival_time=now + timedelta(days=7, hours=10),
                total_seats=180,
                available_seats=180,
                price=Decimal("8500.00"),
                status=FlightStatus.SCHEDULED,
            ),
            Flight(
                id=uuid.uuid4(),
                flight_number="SU5678",
                origin="SVO",
                destination="LED",
                departure_time=now + timedelta(days=7, hours=14),
                arrival_time=now + timedelta(days=7, hours=16),
                total_seats=150,
                available_seats=150,
                price=Decimal("9200.00"),
                status=FlightStatus.SCHEDULED,
            ),
            Flight(
                id=uuid.uuid4(),
                flight_number="DP9012",
                origin="LED",
                destination="SVO",
                departure_time=now + timedelta(days=8, hours=9),
                arrival_time=now + timedelta(days=8, hours=11),
                total_seats=120,
                available_seats=120,
                price=Decimal("7800.00"),
                status=FlightStatus.SCHEDULED,
            ),
        ]
        db.add_all(flights)
        db.commit()
        print(f"Seeded {len(flights)} flights")
    finally:
        db.close()


if __name__ == "__main__":
    seed()