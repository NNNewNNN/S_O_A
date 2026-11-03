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
        "bookings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("flight_id", UUID(as_uuid=True), nullable=False),
        sa.Column("passenger_name", sa.String(255), nullable=False),
        sa.Column("passenger_email", sa.String(255), nullable=False),
        sa.Column("seat_count", sa.Integer, nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("CONFIRMED", "CANCELLED", name="booking_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("seat_count > 0", name="ck_booking_seat_count_positive"),
        sa.CheckConstraint("total_price >= 0", name="ck_booking_total_price_non_negative"),
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])


def downgrade() -> None:
    op.drop_table("bookings")