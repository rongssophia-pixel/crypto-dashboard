"""
Ingestion API Endpoints
Proxy to Ingestion Service via gRPC
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class StartStreamRequest(BaseModel):
    """Start data stream request"""
    symbols: List[str]
    exchange: str = "binance"
    stream_type: str = "ticker"


class StreamStatusResponse(BaseModel):
    """Stream status response"""
    stream_id: str
    is_active: bool
    symbols: List[str]
    events_processed: int


@router.post("/streams/start")
async def start_stream(request: StartStreamRequest):
    """
    Start streaming market data
    
    Calls Ingestion Service via gRPC
    """
    # TODO: Implement
    # 1. Extract tenant context from JWT
    # 2. Call ingestion service gRPC
    # 3. Return response
    pass


@router.post("/streams/{stream_id}/stop")
async def stop_stream(stream_id: str):
    """Stop a running stream"""
    # TODO: Implement
    pass


@router.get("/streams/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(stream_id: str):
    """Get stream status"""
    # TODO: Implement
    pass


@router.get("/streams/active")
async def list_active_streams():
    """List all active streams for tenant"""
    # TODO: Implement
    pass


# TODO: Add historical data fetch endpoint

