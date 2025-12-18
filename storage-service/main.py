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


def create_app():
    """Create FastAPI app for health and metrics"""
    app = FastAPI(title=settings.service_name)

    # Add prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": settings.service_name}

    return app


async def main():
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
    s3_repo = S3Repository(s3_client, settings.s3_bucket_name)
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

    # Run both
    await asyncio.gather(
        start_grpc_server(servicer, settings.service_port), server.serve()
    )


if __name__ == "__main__":
    asyncio.run(main())
