FROM python:3.13-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY analytics-service/requirements_pinned.txt .
RUN pip install --no-cache-dir -r requirements_pinned.txt

# Copy shared modules and proto files
COPY shared /app/shared
COPY proto /app/proto

# Copy analytics service code
COPY analytics-service /app/

# Expose ports
EXPOSE 50052
EXPOSE 8002

# Run the service
CMD ["python", "main.py"]
