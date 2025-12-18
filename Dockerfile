FROM nikolaik/python-nodejs:python3.11-nodejs20

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    supervisor \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install shared requirements
COPY shared/requirements.txt /app/shared/requirements.txt
RUN pip install --no-cache-dir -r /app/shared/requirements.txt

# Copy service requirements and install them
# We install them one by one to leverage caching
COPY analytics-service/requirements.txt /app/analytics-service/requirements.txt
RUN pip install --no-cache-dir -r /app/analytics-service/requirements.txt

COPY api-gateway/requirements.txt /app/api-gateway/requirements.txt
RUN pip install --no-cache-dir -r /app/api-gateway/requirements.txt

COPY ingestion-service/requirements.txt /app/ingestion-service/requirements.txt
RUN pip install --no-cache-dir -r /app/ingestion-service/requirements.txt

COPY notification-service/requirements.txt /app/notification-service/requirements.txt
RUN pip install --no-cache-dir -r /app/notification-service/requirements.txt

COPY storage-service/requirements.txt /app/storage-service/requirements.txt
RUN pip install --no-cache-dir -r /app/storage-service/requirements.txt

COPY stream-processing-service/requirements.txt /app/stream-processing-service/requirements.txt
RUN pip install --no-cache-dir -r /app/stream-processing-service/requirements.txt

# Install shared package in editable mode or just add to pythonpath
# Here we copy the code first
COPY . /app

# Install shared package
RUN pip install -e ./shared

# Generate Protobufs
RUN chmod +x scripts/generate_proto.sh && ./scripts/generate_proto.sh

# Frontend Build
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# Go back to root
WORKDIR /app

# Create log directory for supervisor
RUN mkdir -p /var/log/supervisor

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
# API Gateway
EXPOSE 8000
# Frontend
EXPOSE 3000

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
