"""
Ingestion API Endpoints
Proxy to Ingestion Service via gRPC
"""

import logging
from typing import List, Optional
import grpc
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from config import settings
from proto import ingestion_pb2
from proto import ingestion_pb2_grpc
from proto import common_pb2

logger = logging.getLogger(__name__)

router = APIRouter()

# gRPC channel
_grpc_channel = None
_grpc_stub = None

def get_ingestion_stub() -> ingestion_pb2_grpc.IngestionServiceStub:
    """Get or create gRPC stub for ingestion service"""
    global _grpc_channel, _grpc_stub
    
    if _grpc_stub is None:
        address = f"{settings.ingestion_service_host}:{settings.ingestion_service_port}"
        logger.info(f"Connecting to Ingestion Service at {address}")
        # Try waiting for ready connection
        _grpc_channel = grpc.insecure_channel(address)
        try:
            grpc.channel_ready_future(_grpc_channel).result(timeout=5)
            logger.info("Successfully connected to Ingestion Service")
        except grpc.FutureTimeoutError:
            logger.warning(f"Connection to Ingestion Service at {address} timed out, but proceeding...")
            
        _grpc_stub = ingestion_pb2_grpc.IngestionServiceStub(_grpc_channel)
    
    return _grpc_stub

def close_channel():
    """Close gRPC channel"""
    global _grpc_channel, _grpc_stub
    if _grpc_channel:
        logger.info("Closing Ingestion Service gRPC channel")
        _grpc_channel.close()
        _grpc_channel = None
        _grpc_stub = None

# Request Models
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
    health_status: str

@router.post("/streams/start")
async def start_stream(request: StartStreamRequest):
    """
    Start streaming market data
    
    Calls Ingestion Service via gRPC
    """
    try:
        stub = get_ingestion_stub()
        
        grpc_req = ingestion_pb2.StartStreamRequest(
            symbols=request.symbols,
            exchange=request.exchange,
            stream_type=request.stream_type
        )
        
        response = stub.StartDataStream(grpc_req)
        
        if not response.success:
             raise HTTPException(status_code=400, detail=response.message)

        return {
            "stream_id": response.stream_id,
            "message": response.message,
            "success": response.success
        }
        
    except grpc.RpcError as e:
        logger.error(f"gRPC error in start_stream: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Ingestion service unavailable: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in start_stream: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/streams/{stream_id}/stop")
async def stop_stream(stream_id: str):
    """Stop a running stream"""
    try:
        stub = get_ingestion_stub()
        
        grpc_req = ingestion_pb2.StopStreamRequest(stream_id=stream_id)
        
        # Returns Empty
        stub.StopDataStream(grpc_req)
        
        return {"status": "success", "message": "Stream stopped"}
        
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Stream not found")
            
        logger.error(f"gRPC error in stop_stream: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Ingestion service unavailable: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in stop_stream: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/streams/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(stream_id: str):
    """Get stream status"""
    try:
        stub = get_ingestion_stub()
        
        grpc_req = ingestion_pb2.StreamStatusRequest(stream_id=stream_id)
        
        response = stub.GetStreamStatus(grpc_req)
        
        return StreamStatusResponse(
            stream_id=response.stream_id,
            is_active=response.is_active,
            symbols=list(response.symbols),
            events_processed=response.events_processed,
            health_status=response.health_status
        )
        
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Stream not found")
            
        logger.error(f"gRPC error in get_stream_status: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Ingestion service unavailable: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Error in get_stream_status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/streams/active")
async def list_active_streams():
    """List all active streams"""
    # Note: The proto definition doesn't seem to have a ListActiveStreams RPC.
    # We might need to implement it in the service first or remove this endpoint.
    # For now, return not implemented.
    raise HTTPException(status_code=501, detail="Not implemented")
