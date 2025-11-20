"""
Ingestion Service Main Entry Point
Handles real-time data collection from crypto exchanges
"""

import asyncio
import logging
from concurrent import futures
import grpc

from config import settings
# from api.grpc_server import IngestionServiceServicer
# from api.grpc_servicer import serve

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point for the Ingestion Service
    """
    logger.info(f"Starting {settings.service_name} on port {settings.service_port}")
    
    # TODO: Initialize database connections
    # TODO: Initialize Kafka producer
    # TODO: Start gRPC server
    # TODO: Start Prometheus metrics server
    # TODO: Initialize WebSocket connections to exchanges
    
    logger.info(f"{settings.service_name} is running")
    
    # Keep service running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())

