FROM python:3.11-slim
WORKDIR /app
COPY flight-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY flight-service/ .
COPY proto/ ./proto/
RUN mkdir -p app/generated && \
    python -m grpc_tools.protoc -I./proto \
      --python_out=app/generated \
      --grpc_python_out=app/generated \
      ./proto/flight.proto && \
    sed -i 's/^import flight_pb2 as flight__pb2/from . import flight_pb2 as flight__pb2/' app/generated/flight_pb2_grpc.py && \
    touch app/generated/__init__.py
CMD ["sh", "-c", "alembic upgrade head && python seed.py && python -m app.main"]