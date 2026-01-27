"""
Storage Service Main Entry Point
Handles S3 archival and Athena queries
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import proto and shared modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
import os
from concurrent import futures

import boto3
import grpc
from fastapi import FastAPI
from prometheus_client import make_asgi_app

# Dynamic import for ClickHouseRepository from analytics-service
# (Since 'analytics-service' is not a valid python package name)
import importlib.util

from api.grpc_servicer import StorageServiceServicer
from config import settings
from repositories.athena_repository import AthenaRepository
from repositories.s3_repository import S3Repository
from services.archival_scheduler import ArchivalScheduler
from services.storage_service import StorageBusinessService

ch_repo_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "analytics-service/repositories/clickhouse_repository.py",
)
spec = importlib.util.spec_from_file_location("analytics_clickhouse_repo", ch_repo_path)
analytics_clickhouse_repo = importlib.util.module_from_spec(spec)
sys.modules["analytics_clickhouse_repo"] = analytics_clickhouse_repo
spec.loader.exec_module(analytics_clickhouse_repo)
ClickHouseRepository = analytics_clickhouse_repo.ClickHouseRepository

from repositories.postgres_repository import PostgresRepository

from proto import storage_pb2_grpc

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def start_grpc_server(servicer, port):
    """Start gRPC server"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    storage_pb2_grpc.add_StorageServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info(f"gRPC server started on port {port}")
    await server.wait_for_termination()


# Global reference to scheduler for status endpoint
_archival_scheduler: ArchivalScheduler = None


def create_app():
    """Create FastAPI app for health and metrics"""
    app = FastAPI(title=settings.service_name)

    # Add prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": settings.service_name}

    @app.get("/scheduler/status")
    async def scheduler_status():
        """Get archival scheduler status and job information"""
        if _archival_scheduler:
            return _archival_scheduler.get_status()
        return {"enabled": False, "message": "Archival scheduler not initialized"}

    @app.post("/scheduler/trigger/{job_id}")
    async def trigger_job(job_id: str):
        """Manually trigger an archival job (admin endpoint)"""
        if not _archival_scheduler:
            return {"success": False, "message": "Archival scheduler not initialized"}

        success = await _archival_scheduler.trigger_job(job_id)
        if success:
            return {"success": True, "message": f"Job '{job_id}' triggered"}
        return {"success": False, "message": f"Job '{job_id}' not found"}

    return app


async def main():
    global _archival_scheduler

    logger.info(f"Starting {settings.service_name}...")

    # Initialize AWS Clients
    # Note: In production, use IAM roles. For local dev, use settings.
    session = boto3.Session(
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )

    s3_client = session.client("s3", endpoint_url=settings.aws_endpoint_url)
    athena_client = session.client("athena", endpoint_url=settings.aws_endpoint_url)

    # Initialize Repositories
    # In production (Railway), skip bucket existence check on startup
    # The bucket should already exist with proper IAM permissions
    auto_create = settings.aws_endpoint_url is not None  # Only auto-create for LocalStack
    s3_repo = S3Repository(s3_client, settings.s3_bucket_name, auto_create_bucket=auto_create)
    athena_repo = AthenaRepository(
        athena_client,
        settings.athena_database,
        settings.athena_output_bucket,
        settings.athena_workgroup,
    )

    # ClickHouse Repository (reused from analytics-service for extraction)
    clickhouse_repo = ClickHouseRepository(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_db,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        secure=settings.clickhouse_secure,
        verify=settings.clickhouse_verify,
    )
    await clickhouse_repo.connect()

    # Postgres Repository
    postgres_repo = PostgresRepository(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )

    # Initialize Business Service
    storage_service = StorageBusinessService(
        s3_repo, athena_repo, clickhouse_repo, postgres_repo
    )

    # Initialize Archival Scheduler (if enabled)
    if settings.archival_enabled:
        database_url = (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )

        _archival_scheduler = ArchivalScheduler(
            database_url=database_url,
            market_data_ttl_hours=settings.market_data_ttl_hours,
            market_candles_ttl_hours=settings.market_candles_ttl_hours,
            market_data_cron=settings.archival_market_data_cron,
            market_candles_cron=settings.archival_market_candles_cron,
            # AWS Config
            aws_endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_region=settings.aws_region,
            s3_bucket_name=settings.s3_bucket_name,
            athena_output_bucket=settings.athena_output_bucket,
            athena_database=settings.athena_database,
            athena_workgroup=settings.athena_workgroup,
            # ClickHouse Config
            clickhouse_host=settings.clickhouse_host,
            clickhouse_port=settings.clickhouse_port,
            clickhouse_db=settings.clickhouse_db,
            clickhouse_user=settings.clickhouse_user,
            clickhouse_password=settings.clickhouse_password,
            clickhouse_secure=settings.clickhouse_secure,
            clickhouse_verify=settings.clickhouse_verify,
            # PostgreSQL Config
            postgres_host=settings.postgres_host,
            postgres_port=settings.postgres_port,
            postgres_db=settings.postgres_db,
            postgres_user=settings.postgres_user,
            postgres_password=settings.postgres_password,
        )
        _archival_scheduler.start()
        logger.info(
            "Archival scheduler started with PostgreSQL persistence: "
            "market_data_ttl=%dh (cron: %s), market_candles_ttl=%dh (cron: %s)",
            settings.market_data_ttl_hours,
            settings.archival_market_data_cron,
            settings.market_candles_ttl_hours,
            settings.archival_market_candles_cron,
        )
    else:
        logger.info("Archival scheduler is disabled")

    # Initialize gRPC Servicer
    servicer = StorageServiceServicer(storage_service)

    # Start gRPC Server and FastAPI app
    # We run gRPC in the main loop and FastAPI in uvicorn

    # For simplicity in this setup, we'll run gRPC as the main task
    # and let uvicorn run in a separate process or thread if needed.
    # But usually, we might want to run both.
    # Let's run gRPC here. FastAPI can be run via uvicorn CLI in a separate container/process
    # OR we can run uvicorn programmatically.

    # Running uvicorn in asyncio loop
    import uvicorn

    config = uvicorn.Config(
        create_app(), host="0.0.0.0", port=settings.http_port, log_level="info"
    )
    server = uvicorn.Server(config)

    try:
        # Run both gRPC and HTTP servers
        await asyncio.gather(
            start_grpc_server(servicer, settings.service_port), server.serve()
        )
    finally:
        # Cleanup on shutdown
        if _archival_scheduler:
            logger.info("Stopping archival scheduler...")
            _archival_scheduler.stop()
            logger.info("Archival scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
