"""
Storage Service Main Entry Point
Handles S3 archival and Athena queries
"""

import asyncio
import logging
from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    logger.info(f"Starting {settings.service_name} on port {settings.service_port}")
    
    # TODO: Initialize S3 client
    # TODO: Initialize Athena client
    # TODO: Start gRPC server
    
    logger.info(f"{settings.service_name} is running")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())

