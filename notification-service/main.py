"""
Notification Service Main Entry Point
Handles alert delivery via email, SMS, SNS, etc.
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import proto and shared modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
from contextlib import asynccontextmanager

import asyncpg
import grpc
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from config import settings
from repositories.notification_repository import NotificationRepository
from providers.email_provider import MockEmailProvider
from services.notification_service import NotificationBusinessService, set_metrics
from services.retry_service import RetryService
from consumers.alert_consumer import AlertConsumer
from api.grpc_servicer import NotificationServiceServicer
from proto import notification_pb2_grpc


# Metrics module for business service
class MetricsModule:
    """Container for metrics to pass to business service"""
    def __init__(self):
        self.notifications_sent_total = notifications_sent_total
        self.notification_send_duration_seconds = notification_send_duration_seconds
        self.pending_notifications = pending_notifications
        self.failed_notifications = failed_notifications
        self.kafka_messages_consumed = kafka_messages_consumed
        self.retry_attempts_total = retry_attempts_total

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Prometheus metrics
notifications_sent_total = Counter(
    'notifications_sent_total',
    'Total number of notifications sent',
    ['status', 'type']
)

notification_send_duration_seconds = Histogram(
    'notification_send_duration_seconds',
    'Time to send notification',
    ['type']
)

pending_notifications = Gauge(
    'pending_notifications',
    'Number of pending notifications'
)

failed_notifications = Gauge(
    'failed_notifications',
    'Number of failed notifications'
)

kafka_messages_consumed = Counter(
    'kafka_messages_consumed_total',
    'Total Kafka messages consumed',
    ['topic']
)

retry_attempts_total = Counter(
    'retry_attempts_total',
    'Total notification retry attempts'
)

# Global state for health checks
app_state = {
    "db_pool": None,
    "alert_consumer": None,
    "retry_service": None,
    "business_service": None,
    "email_provider": None,
    "grpc_server": None
}


async def create_db_pool() -> asyncpg.Pool:
    """Create PostgreSQL connection pool"""
    logger.info(
        f"Connecting to PostgreSQL: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        min_size=2,
        max_size=10
    )
    logger.info("Database connection pool created")
    return pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.service_name}...")
    
    # Set up metrics for business service
    set_metrics(MetricsModule())
    
    # Initialize database connection pool
    db_pool = await create_db_pool()
    app_state["db_pool"] = db_pool
    
    # Initialize notification repository
    notification_repo = NotificationRepository(db_pool)
    
    # Initialize email provider (mock for development)
    email_provider = MockEmailProvider(failure_rate=0.0)
    app_state["email_provider"] = email_provider
    
    # Initialize business service
    business_service = NotificationBusinessService(
        notification_repository=notification_repo,
        email_provider=email_provider
    )
    app_state["business_service"] = business_service
    
    # Initialize and start Kafka alert consumer
    alert_consumer = AlertConsumer(
        business_service=business_service,
        kafka_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_topic_alerts,
        group_id=settings.kafka_consumer_group,
        security_protocol=settings.kafka_security_protocol,
        sasl_mechanism=settings.kafka_sasl_mechanism,
        sasl_plain_username=settings.kafka_sasl_username,
        sasl_plain_password=settings.kafka_sasl_password,
    )
    app_state["alert_consumer"] = alert_consumer
    consumer_task = asyncio.create_task(alert_consumer.start())
    
    # Initialize and start retry service
    retry_service = RetryService(
        notification_repo=notification_repo,
        business_service=business_service,
        max_retries=settings.max_retry_attempts,
        check_interval=settings.retry_interval_seconds
    )
    app_state["retry_service"] = retry_service
    await retry_service.start()
    
    # Initialize and start gRPC server
    grpc_server = grpc.aio.server()
    servicer = NotificationServiceServicer(
        business_service=business_service,
        notification_repo=notification_repo
    )
    notification_pb2_grpc.add_NotificationServiceServicer_to_server(servicer, grpc_server)
    grpc_server.add_insecure_port(f'[::]:{settings.service_port}')
    await grpc_server.start()
    app_state["grpc_server"] = grpc_server
    logger.info(f"gRPC server started on port {settings.service_port}")
    
    logger.info(f"{settings.service_name} started successfully")
    
    yield
    
    # Cleanup
    logger.info(f"Shutting down {settings.service_name}...")
    
    # Stop gRPC server
    if grpc_server:
        logger.info("Stopping gRPC server...")
        await grpc_server.stop(grace=5)
    
    # Stop retry service
    await retry_service.stop()
    
    # Stop Kafka consumer
    await alert_consumer.stop()
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    
    # Close database pool
    await db_pool.close()
    logger.info(f"{settings.service_name} shutdown complete")

app = FastAPI(
    title="Crypto Notification Service",
    description="Alert delivery service",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/")
async def root():
    return {
        "service": settings.service_name,
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """
    Comprehensive health check
    Returns status of all critical components
    """
    health_status = {
        "status": "healthy",
        "service": settings.service_name,
        "components": {}
    }
    
    # Check database connection
    try:
        if app_state["db_pool"]:
            async with app_state["db_pool"].acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["components"]["database"] = "healthy"
        else:
            health_status["components"]["database"] = "not initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Kafka consumer
    try:
        if app_state["alert_consumer"]:
            if app_state["alert_consumer"].is_running():
                health_status["components"]["kafka_consumer"] = "healthy"
            else:
                health_status["components"]["kafka_consumer"] = "stopped"
                health_status["status"] = "degraded"
        else:
            health_status["components"]["kafka_consumer"] = "not initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["kafka_consumer"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check retry service
    try:
        if app_state["retry_service"]:
            if app_state["retry_service"].is_running():
                health_status["components"]["retry_service"] = "healthy"
            else:
                health_status["components"]["retry_service"] = "stopped"
                health_status["status"] = "degraded"
        else:
            health_status["components"]["retry_service"] = "not initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["retry_service"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check email provider
    try:
        if app_state["email_provider"]:
            health_status["components"]["email_provider"] = "healthy"
        else:
            health_status["components"]["email_provider"] = "not initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["email_provider"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check gRPC server
    try:
        if app_state["grpc_server"]:
            health_status["components"]["grpc_server"] = "healthy"
        else:
            health_status["components"]["grpc_server"] = "not initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["grpc_server"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

async def main():
    # Start gRPC server placeholder
    # In a real implementation, we'd start the gRPC server here too, 
    # potentially using asyncio.gather to run both gRPC and HTTP servers.
    logger.info(f"Starting {settings.service_name}...")
    
    # Run FastAPI app (for metrics and health)
    import uvicorn
    # Use prometheus_port for HTTP/metrics access as per prometheus.yml
    logger.info(f"Starting HTTP server on port {settings.prometheus_port}")
    
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=settings.prometheus_port, 
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
