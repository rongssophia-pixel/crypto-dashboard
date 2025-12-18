"""
API Gateway Main Entry Point
Unified REST API for all services
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import proto and shared modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from api import analytics, auth, ingestion, storage, websocket
from config import settings
from services.websocket_manager import ConnectionManager
from services.kafka_consumer_service import WebSocketKafkaConsumer
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

# from middleware.auth_middleware import verify_token

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ========================================
# PROMETHEUS METRICS
# ========================================
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        process_time = time.time() - start_time
        
        # Record metrics (skip metrics endpoint itself to avoid noise)
        if request.url.path != "/metrics":
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(process_time)
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager
    Manages startup and shutdown of all service resources
    """
    # Startup
    logger.info(f"Starting {settings.service_name}...")
    
    # Initialize WebSocket components
    logger.info("Initializing WebSocket components...")
    connection_manager = ConnectionManager.get_instance()
    kafka_consumer = WebSocketKafkaConsumer(connection_manager)
    
    # Store in app state
    app.state.ws_manager = connection_manager
    app.state.kafka_consumer = kafka_consumer
    
    # Start Kafka consumer
    try:
        await kafka_consumer.start()
        logger.info("Kafka consumer started successfully")
        
        # Start consumer loop in background
        consume_task = asyncio.create_task(kafka_consumer.consume_loop())
        app.state.consume_task = consume_task
        logger.info("Kafka consume loop started")
        
    except Exception as e:
        logger.error(f"Failed to start Kafka consumer: {e}", exc_info=True)
        logger.warning("WebSocket will run without Kafka streaming")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}...")
    
    # Stop Kafka consumer
    if hasattr(app.state, "kafka_consumer"):
        await app.state.kafka_consumer.stop()
    
    # Cancel consume task
    if hasattr(app.state, "consume_task"):
        app.state.consume_task.cancel()
        try:
            await app.state.consume_task
        except asyncio.CancelledError:
            pass

    # Close gRPC channels
    if hasattr(analytics, "close_channel"):
        analytics.close_channel()
    if hasattr(ingestion, "close_channel"):
        ingestion.close_channel()
    if hasattr(storage, "close_channel"):
        storage.close_channel()


app = FastAPI(
    title="Crypto Analytics Platform API",
    description="Real-time crypto market data analytics platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus Middleware
app.add_middleware(PrometheusMiddleware)

# Security
security = HTTPBearer()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"service": settings.service_name, "status": "running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    # TODO: Check connectivity to all downstream services
    return {
        "status": "healthy",
        "services": {
            "ingestion": "unknown",
            "analytics": "unknown",
            "storage": "unknown",
            "notification": "unknown",
        },
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Include routers from api modules
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(storage.router, prefix="/api/v1/storage", tags=["Storage"])
app.include_router(websocket.router, tags=["WebSocket"])
# app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
