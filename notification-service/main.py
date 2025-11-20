"""
Notification Service Main Entry Point
Handles alert delivery via email, SMS, SNS, etc.
"""

import asyncio
import logging
from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    logger.info(f"Starting {settings.service_name} on port {settings.service_port}")
    
    # TODO: Initialize database connection
    # TODO: Initialize notification providers
    # TODO: Start gRPC server
    
    logger.info(f"{settings.service_name} is running")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())

