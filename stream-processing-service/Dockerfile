FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY stream-processing-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared /app/shared

# Copy proto generated files
COPY proto /app/proto

# Copy service code
COPY stream-processing-service /app/

# Expose ports
EXPOSE 8005
EXPOSE 50055

# Run the service
CMD ["python", "main.py"]
