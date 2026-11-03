import logging

from fastapi import FastAPI

from app.routers import bookings, flights

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

app = FastAPI(title="Booking Service", version="1.0.0")
app.include_router(flights.router)
app.include_router(bookings.router)


@app.get("/health")
def health():
    return {"status": "ok"}