"""
Ingestion Service Main Entry Point
Handles real-time data collection from crypto exchanges
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from concurrent import futures

from fastapi import FastAPI, Depends
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram, Gauge
import grpc
from psycopg2.pool import SimpleConnectionPool

from config import settings
from api.grpc_servicer import IngestionServiceServicer
from services.ingestion_service import IngestionBusinessService
from repositories.stream_repository import StreamRepository
from repositories.kafka_repository import KafkaRepository
from connectors.binance_connector import BinanceConnector
from shared.kafka_utils.producer import KafkaProducerWrapper
from proto import ingestion_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========================================
# PROMETHEUS METRICS
# ========================================
# Helper function to safely create or get existing metrics
def get_or_create_counter(name, description, labelnames):
    """Get existing counter or create new one"""
    from prometheus_client import REGISTRY
    
    # Try to find existing metric
    # For counters, strip _total suffix if present when checking _name
    base_name = name.replace('_total', '') if name.endswith('_total') else name
    
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == base_name:
            return collector
    
    # If not found, create new one
    try:
        return Counter(name, description, labelnames)
    except ValueError:
        # If we still get a duplicate error, try to find it again
        for collector in list(REGISTRY._collector_to_names.keys()):
            if hasattr(collector, '_name') and collector._name == base_name:
                return collector
        raise

def get_or_create_gauge(name, description, labelnames):
    """Get existing gauge or create new one"""
    from prometheus_client import REGISTRY
    
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    
    try:
        return Gauge(name, description, labelnames)
    except ValueError:
        for collector in list(REGISTRY._collector_to_names.keys()):
            if hasattr(collector, '_name') and collector._name == name:
                return collector
        raise

def get_or_create_histogram(name, description, labelnames):
    """Get existing histogram or create new one"""
    from prometheus_client import REGISTRY
    
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    
    try:
        return Histogram(name, description, labelnames)
    except ValueError:
        for collector in list(REGISTRY._collector_to_names.keys()):
            if hasattr(collector, '_name') and collector._name == name:
                return collector
        raise

# Initialize metrics
RECORDS_RECEIVED = get_or_create_counter(
    "ingestion_records_received_total",
    "Total records received from exchanges",
    ["exchange", "stream_type", "symbol"]
)

RECORDS_PUBLISHED = get_or_create_counter(
    "ingestion_records_published_total",
    "Total records published to Kafka",
    ["exchange", "stream_type", "symbol", "topic"]
)

RECORDS_FAILED = get_or_create_counter(
    "ingestion_records_failed_total",
    "Total records that failed to publish",
    ["exchange", "stream_type", "symbol", "reason"]
)

ACTIVE_STREAMS = get_or_create_gauge(
    "ingestion_active_streams",
    "Number of active ingestion streams",
    ["exchange", "stream_type"]
)

PROCESSING_LATENCY = get_or_create_histogram(
    "ingestion_processing_duration_seconds",
    "Time to process and publish record",
    ["exchange", "stream_type"]
)


class AppState:
    """Centralized application state container"""
    # Infrastructure resources
    db_pool: SimpleConnectionPool = None
    kafka_producer: KafkaProducerWrapper = None
    binance_connector: BinanceConnector = None
    
    # Repositories
    stream_repository: StreamRepository = None
    kafka_repository: KafkaRepository = None
    
    # Business service
    ingestion_service: IngestionBusinessService = None
    
    # Servers
    grpc_server = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    FastAPI lifespan context manager
    Manages startup and shutdown of all service resources
    """
    # ========================================
    # STARTUP PHASE
    # ========================================
    logger.info(f"🚀 Starting {settings.service_name}...")
    
    try:
        # 1. Initialize PostgreSQL connection pool
        logger.info("Initializing PostgreSQL connection pool...")
        app_state.db_pool = SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        logger.info("✅ PostgreSQL pool initialized")
        
        # 2. Initialize Kafka producer
        logger.info("Initializing Kafka producer...")
        app_state.kafka_producer = KafkaProducerWrapper(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id=f"{settings.service_name}-producer",
        )
        logger.info("✅ Kafka producer initialized")
        
        # 3. Initialize Binance connector
        logger.info("Initializing Binance connector...")
        app_state.binance_connector = BinanceConnector(
            websocket_url=settings.binance_websocket_url,
            api_key=settings.binance_api_key,
            api_secret=settings.binance_api_secret,
        )
        logger.info("✅ Binance connector initialized")
        
        # 4. Initialize repositories
        logger.info("Initializing repositories...")
        app_state.stream_repository = StreamRepository(app_state.db_pool)
        app_state.kafka_repository = KafkaRepository(app_state.kafka_producer)
        logger.info("✅ Repositories initialized")
        
        # 5. Initialize business service
        logger.info("Initializing ingestion business service...")
        app_state.ingestion_service = IngestionBusinessService(
            stream_repository=app_state.stream_repository,
            kafka_repository=app_state.kafka_repository,
            binance_connector=app_state.binance_connector,
        )
        logger.info("✅ Ingestion business service initialized")
        
        # 6. Start gRPC server (for inter-service communication)
        logger.info(f"Starting gRPC server on port {settings.service_port}...")
        app_state.grpc_server = grpc.aio.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=[
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ]
        )
        
        # Add servicer to gRPC server
        ingestion_pb2_grpc.add_IngestionServiceServicer_to_server(
            IngestionServiceServicer(app_state.ingestion_service, settings.kafka_topic_raw_market_data),
            app_state.grpc_server
        )
        
        app_state.grpc_server.add_insecure_port(f"[::]:{settings.service_port}")
        await app_state.grpc_server.start()
        logger.info(f"✅ gRPC server started on port {settings.service_port}")
        
        # Service ready
        logger.info("=" * 60)
        logger.info(f"✅ {settings.service_name} is ready!")
        logger.info(f"   - HTTP/FastAPI: port {settings.http_port}")
        logger.info(f"   - gRPC: port {settings.service_port}")
        logger.info("=" * 60)
        
        # Yield control to the application
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start {settings.service_name}: {e}", exc_info=True)
        raise
    
    finally:
        # ========================================
        # SHUTDOWN PHASE
        # ========================================
        logger.info("=" * 60)
        logger.info(f"🛑 Shutting down {settings.service_name}...")
        logger.info("=" * 60)
        
        # 1. Stop all active streams
        if app_state.ingestion_service:
            try:
                logger.info("Stopping all active streams...")
                active_stream_ids = list(app_state.ingestion_service.active_streams.keys())
                for stream_id in active_stream_ids:
                    await app_state.ingestion_service.stop_stream(
                        stream_id=stream_id
                    )
                logger.info(f"✅ Stopped {len(active_stream_ids)} active stream(s)")
            except Exception as e:
                logger.error(f"Error stopping streams: {e}")
        
        # 2. Stop gRPC server
        if app_state.grpc_server:
            try:
                logger.info("Stopping gRPC server...")
                await app_state.grpc_server.stop(grace=5.0)
                logger.info("✅ gRPC server stopped")
            except Exception as e:
                logger.error(f"Error stopping gRPC server: {e}")
        
        # 3. Close Binance connector
        if app_state.binance_connector:
            try:
                logger.info("Closing Binance connector...")
                await app_state.binance_connector.close()
                logger.info("✅ Binance connector closed")
            except Exception as e:
                logger.error(f"Error closing Binance connector: {e}")
        
        # 4. Close Kafka producer
        if app_state.kafka_producer:
            try:
                logger.info("Closing Kafka producer...")
                app_state.kafka_producer.flush(timeout=10)
                app_state.kafka_producer.close()
                logger.info("✅ Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
        
        # 5. Close database pool
        if app_state.db_pool:
            try:
                logger.info("Closing database connection pool...")
                app_state.db_pool.closeall()
                logger.info("✅ Database pool closed")
            except Exception as e:
                logger.error(f"Error closing database pool: {e}")
        
        logger.info("=" * 60)
        logger.info(f"✅ {settings.service_name} shutdown complete")
        logger.info("=" * 60)


# ========================================
# CREATE FASTAPI APP
# ========================================
app = FastAPI(
    title="Crypto Ingestion Service",
    description="Real-time crypto market data ingestion from exchanges",
    version="1.0.0",
    lifespan=lifespan,
)


# ========================================
# DEPENDENCY INJECTION
# ========================================
def get_ingestion_service() -> IngestionBusinessService:
    """Dependency injection for ingestion business service"""
    if app_state.ingestion_service is None:
        raise RuntimeError("Ingestion service not initialized")
    return app_state.ingestion_service


# ========================================
# HTTP ENDPOINTS (Monitoring & Admin)
# ========================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
        "description": "Real-time crypto market data ingestion service"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and orchestration
    Used by Kubernetes liveness/readiness probes
    """
    health_status = {
        "service": settings.service_name,
        "status": "healthy",
        "checks": {
            "grpc_server": app_state.grpc_server is not None,
            "ingestion_service": app_state.ingestion_service is not None,
            "database_pool": app_state.db_pool is not None and app_state.db_pool.closed == 0,
            "kafka_producer": app_state.kafka_producer is not None,
            "binance_connector": app_state.binance_connector is not None,
        }
    }
    
    # Add active streams count
    if app_state.ingestion_service:
        health_status["active_streams"] = len(app_state.ingestion_service.active_streams)
    
    # Determine overall health
    all_healthy = all(health_status["checks"].values())
    health_status["status"] = "healthy" if all_healthy else "degraded"
    
    return health_status


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    Exposes service metrics for monitoring
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/debug/streams")
async def debug_streams(service: IngestionBusinessService = Depends(get_ingestion_service)):
    """
    Debug endpoint - list all active streams
    Should be protected or removed in production
    """
    streams = []
    for stream_id, stream_info in service.active_streams.items():
        streams.append({
            "stream_id": stream_id,
            "symbols": stream_info["symbols"],
            "exchange": stream_info["exchange"],
            "stream_type": stream_info["stream_type"],
            "started_at": stream_info["started_at"].isoformat(),
        })
    
    return {
        "total_active_streams": len(streams),
        "streams": streams
    }


# ========================================
# RUN THE APP
# ========================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.http_port,
        log_level="info",
        access_log=True,
    )
