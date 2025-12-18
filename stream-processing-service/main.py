"""
Stream Processing Service Main Entry Point
Handles data transformation and aggregation from Kafka to ClickHouse
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import proto and shared modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from config import settings
from shared.kafka_utils import KafkaConsumerWrapper
from sinks.clickhouse_sink import ClickHouseSink
from services.job_manager import JobManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AppState:
    """Centralized application state container"""
    # Infrastructure
    kafka_consumer: KafkaConsumerWrapper = None
    clickhouse_sink: ClickHouseSink = None
    
    # Services
    job_manager: JobManager = None


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
        # 1. Initialize ClickHouse sink
        logger.info("Initializing ClickHouse sink...")
        app_state.clickhouse_sink = ClickHouseSink(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            database=settings.clickhouse_db,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            batch_size=settings.batch_size,
            flush_interval=settings.flush_interval_seconds,
        )
        await app_state.clickhouse_sink.start()
        logger.info("✅ ClickHouse sink initialized")
        
        # 2. Initialize Kafka consumer
        logger.info("Initializing Kafka consumer...")
        app_state.kafka_consumer = KafkaConsumerWrapper(
            topics=[settings.kafka_topic_raw_market_data],
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            auto_offset_reset="earliest",  # Changed from "latest" to process all messages
        )
        logger.info("✅ Kafka consumer initialized")
        
        # 3. Initialize Job Manager
        logger.info("Initializing Job Manager...")
        app_state.job_manager = JobManager(
            kafka_consumer=app_state.kafka_consumer,
            clickhouse_sink=app_state.clickhouse_sink,
            candle_intervals=settings.candle_interval_list,
        )
        logger.info("✅ Job Manager initialized")
        
        # 4. Start processing pipeline
        logger.info("Starting processing pipeline...")
        await app_state.job_manager.start()
        logger.info("✅ Processing pipeline started")
        
        # Service ready
        logger.info("=" * 60)
        logger.info(f"✅ {settings.service_name} is ready!")
        logger.info(f"   - HTTP/FastAPI: port {settings.http_port}")
        logger.info(f"   - Consuming from: {settings.kafka_topic_raw_market_data}")
        logger.info(f"   - Writing to ClickHouse: {settings.clickhouse_host}:{settings.clickhouse_port}")
        logger.info(f"   - Candle intervals: {settings.candle_interval_list}")
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
        
        # 1. Stop Job Manager (stops consumer and jobs)
        if app_state.job_manager:
            try:
                logger.info("Stopping Job Manager...")
                await app_state.job_manager.stop()
                logger.info("✅ Job Manager stopped")
            except Exception as e:
                logger.error(f"Error stopping Job Manager: {e}")
        
        # 2. Stop ClickHouse sink
        if app_state.clickhouse_sink:
            try:
                logger.info("Stopping ClickHouse sink...")
                await app_state.clickhouse_sink.stop()
                logger.info("✅ ClickHouse sink stopped")
            except Exception as e:
                logger.error(f"Error stopping ClickHouse sink: {e}")
        
        logger.info("=" * 60)
        logger.info(f"✅ {settings.service_name} shutdown complete")
        logger.info("=" * 60)


# ========================================
# CREATE FASTAPI APP
# ========================================
app = FastAPI(
    title="Stream Processing Service",
    description="Real-time data transformation and aggregation service",
    version="1.0.0",
    lifespan=lifespan,
)


# ========================================
# DEPENDENCY INJECTION
# ========================================
def get_job_manager() -> JobManager:
    """Dependency injection for job manager"""
    if app_state.job_manager is None:
        raise RuntimeError("Job manager not initialized")
    return app_state.job_manager


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
        "description": "Stream processing and aggregation service"
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
            "job_manager": app_state.job_manager is not None,
            "kafka_consumer": (
                app_state.kafka_consumer is not None 
                and app_state.kafka_consumer.is_running
            ),
            "clickhouse_sink": (
                app_state.clickhouse_sink is not None 
                and app_state.clickhouse_sink._running
            ),
        }
    }
    
    # Add job stats
    if app_state.job_manager:
        health_status["is_healthy"] = app_state.job_manager.is_healthy
        health_status["messages_processed"] = app_state.job_manager._message_count
    
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


@app.get("/stats")
async def get_stats(job_manager: JobManager = Depends(get_job_manager)):
    """
    Get detailed processing statistics
    """
    return job_manager.get_stats()


@app.get("/debug/sink")
async def debug_sink():
    """
    Debug endpoint - ClickHouse sink stats
    """
    if app_state.clickhouse_sink:
        return app_state.clickhouse_sink.get_stats()
    return {"error": "Sink not initialized"}


@app.get("/debug/consumer")
async def debug_consumer():
    """
    Debug endpoint - Kafka consumer stats
    """
    if app_state.kafka_consumer:
        return {
            "is_running": app_state.kafka_consumer.is_running,
            "topics": app_state.kafka_consumer.topics,
            "group_id": app_state.kafka_consumer.group_id,
        }
    return {"error": "Consumer not initialized"}


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
