FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ingestion-service/requirements_pinned.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared /app/shared

# Copy proto generated files
COPY proto /app/proto

# Copy service code
COPY ingestion-service /app/

# Expose ports
EXPOSE 50051
EXPOSE 8001

# Run the service
CMD ["python", "main.py"]