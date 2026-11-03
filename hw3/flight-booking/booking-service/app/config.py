import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://booking_user:booking_pass@localhost:5434/bookings",
)
FLIGHT_SERVICE_HOST = os.getenv("FLIGHT_SERVICE_HOST", "localhost")
FLIGHT_SERVICE_PORT = int(os.getenv("FLIGHT_SERVICE_PORT", "50051"))
API_KEY = os.getenv("API_KEY", "dev-key")

CB_FAILURE_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "5"))
CB_RECOVERY_TIMEOUT = int(os.getenv("CB_RECOVERY_TIMEOUT", "30"))

RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 0.1