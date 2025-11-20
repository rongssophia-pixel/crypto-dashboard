"""
Analytics Service Main Entry Point
Real-time query engine for market data
"""

import asyncio
import logging

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for Analytics Service"""
    logger.info(f"Starting {settings.service_name} on port {settings.service_port}")
    
    # TODO: Initialize ClickHouse connection
    # TODO: Start gRPC server
    # TODO: Start Prometheus metrics server
    
    logger.info(f"{settings.service_name} is running")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())

