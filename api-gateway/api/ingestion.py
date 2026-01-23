"""
Ingestion API Endpoints
Provides status information about the auto-ingestion service
"""

import logging
import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestionStatus(BaseModel):
    """Ingestion service status"""
    active_connections: int
    symbols_count: int
    symbols: List[str]
    is_running: bool


@router.get("/status", response_model=IngestionStatus)
async def get_ingestion_status():
    """
    Get current ingestion service status
    
    Returns information about active ingestion connections and symbols
    """
    try:
        # Call ingestion service HTTP endpoint
        ingestion_url = f"http://{settings.ingestion_service_host}:{settings.ingestion_service_http_port}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ingestion_url}/status", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    return IngestionStatus(**data)
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Ingestion service unavailable"
                    )
                    
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to ingestion service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to ingestion service"
        )
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def check_ingestion_health():
    """
    Check if ingestion service is healthy
    """
    try:
        ingestion_url = f"http://{settings.ingestion_service_host}:{settings.ingestion_service_http_port}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ingestion_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Ingestion service unhealthy"
                    )
                    
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to ingestion service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to ingestion service"
        )
    except Exception as e:
        logger.error(f"Error checking ingestion health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
