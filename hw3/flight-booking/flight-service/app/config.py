import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://flight_user:flight_pass@localhost:5433/flights",
)
REDIS_SENTINELS = os.getenv("REDIS_SENTINELS", "localhost:26379")
REDIS_MASTER = os.getenv("REDIS_MASTER", "mymaster")
API_KEY = os.getenv("API_KEY", "dev-key")