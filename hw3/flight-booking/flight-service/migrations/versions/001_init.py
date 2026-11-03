"""init

Revision ID: 001
Revises:
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("flight_number", sa.String(10), nullable=False),
        sa.Column("origin", sa.String(3), nullable=False),
        sa.Column("destination", sa.String(3), nullable=False),
        sa.Column("departure_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrival_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_seats", sa.Integer, nullable=False),
        sa.Column("available_seats", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("SCHEDULED", "DEPARTED", "CANCELLED", "COMPLETED", name="flight_status"),
            nullable=False,
        ),
        sa.CheckConstraint("total_seats > 0", name="ck_total_seats_positive"),
        sa.CheckConstraint("available_seats >= 0", name="ck_available_seats_non_negative"),
        sa.CheckConstraint("price > 0", name="ck_price_positive"),
        sa.CheckConstraint("arrival_time > departure_time", name="ck_arrival_after_departure"),
        sa.UniqueConstraint("flight_number", "departure_time", name="uq_flight_number_date"),
    )
    op.create_index("ix_flights_route_date", "flights", ["origin", "destination", "departure_time"])

    op.create_table(
        "seat_reservations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("flight_id", UUID(as_uuid=True), sa.ForeignKey("flights.id"), nullable=False),
        sa.Column("booking_id", sa.String(255), unique=True, nullable=False),
        sa.Column("seat_count", sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "RELEASED", "EXPIRED", name="reservation_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("seat_count > 0", name="ck_seat_count_positive"),
    )
    op.create_index("ix_reservations_booking_id", "seat_reservations", ["booking_id"], unique=True)


def downgrade() -> None:
    op.drop_table("seat_reservations")
    op.drop_table("flights")