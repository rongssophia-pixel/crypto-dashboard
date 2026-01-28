"""
Storage API Endpoints
Proxy to Storage Service via gRPC
"""

import httpx
import logging
from datetime import datetime
from typing import List

from config import settings
from fastapi import APIRouter, Depends, HTTPException, Query
from middleware.auth_middleware import require_auth
from shared.auth.jwt_handler import UserContext

from proto import common_pb2, storage_pb2
from shared.grpc_client.client_factory import GRPCClientFactory

logger = logging.getLogger(__name__)

router = APIRouter()

# Use a module-level factory instance
_client_factory = GRPCClientFactory()


def get_storage_client():
    """Get storage service gRPC client"""
    return _client_factory.get_storage_client(
        settings.storage_service_host, settings.storage_service_port
    )


def close_channel():
    """Close gRPC channels"""
    _client_factory.close_all()


@router.post("/archive")
async def archive_data(
    start_time: datetime,
    end_time: datetime,
    data_type: str,
    symbols: List[str] = Query(None),
    current_user: UserContext = Depends(require_auth),
):
    """Trigger archive job"""
    client = get_storage_client()
    try:
        user_id = current_user.user_id
        roles = current_user.roles

        request = storage_pb2.ArchiveRequest(
            context=common_pb2.UserContext(user_id=user_id, roles=roles),
            start_time=common_pb2.Timestamp(seconds=int(start_time.timestamp())),
            end_time=common_pb2.Timestamp(seconds=int(end_time.timestamp())),
            data_type=data_type,
            symbols=symbols or [],
        )
        response = client.ArchiveData(request)
        return {
            "archive_id": response.archive_id,
            "success": response.success,
            "s3_path": response.s3_path,
            "message": response.message,
            "records_count": response.records_count,
        }
    except Exception as e:
        logger.error(f"Error in archive_data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_archive(
    sql_query: str,
    max_results: int = 1000,
    current_user: UserContext = Depends(require_auth),
):
    """Query archived data"""
    client = get_storage_client()
    try:
        user_id = current_user.user_id
        roles = current_user.roles

        request = storage_pb2.ArchiveQueryRequest(
            context=common_pb2.UserContext(user_id=user_id, roles=roles),
            sql_query=sql_query,
            max_results=max_results,
        )
        response = client.QueryArchive(request)

        rows = []
        for row in response.rows:
            rows.append(dict(row.values))

        return {
            "rows": rows,
            "column_names": response.column_names,
            "row_count": response.row_count,
            "execution_id": response.execution_id,
        }
    except Exception as e:
        logger.error(f"Error in query_archive: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archives")
async def list_archives(
    limit: int = 20,
    offset: int = 0,
    current_user: UserContext = Depends(require_auth),
):
    """List archives"""
    client = get_storage_client()
    try:
        user_id = current_user.user_id
        roles = current_user.roles

        request = storage_pb2.ListArchivesRequest(
            context=common_pb2.UserContext(user_id=user_id, roles=roles),
            limit=limit,
            offset=offset,
        )
        response = client.ListArchives(request)

        archives = []
        for arch in response.archives:
            created_at = None
            if arch.created_at and arch.created_at.seconds > 0:
                created_at = datetime.fromtimestamp(arch.created_at.seconds).isoformat()

            archives.append(
                {
                    "archive_id": arch.archive_id,
                    "s3_path": arch.s3_path,
                    "created_at": created_at,
                    "records_count": arch.records_count,
                    "data_type": arch.data_type,
                    "size_bytes": arch.size_bytes,
                }
            )

        return {
            "archives": archives,
            "total_count": response.total_count,
        }
    except Exception as e:
        logger.error(f"Error in list_archives: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archives/{archive_id}/status")
async def get_archive_status(
    archive_id: str,
    current_user: UserContext = Depends(require_auth),
):
    """Get archive status"""
    client = get_storage_client()
    try:
        user_id = current_user.user_id
        roles = current_user.roles

        request = storage_pb2.ArchiveStatusRequest(
            context=common_pb2.UserContext(user_id=user_id, roles=roles),
            archive_id=archive_id,
        )
        response = client.GetArchiveStatus(request)

        created_at = None
        if response.created_at and response.created_at.seconds > 0:
            created_at = datetime.fromtimestamp(response.created_at.seconds).isoformat()

        completed_at = None
        if response.completed_at and response.completed_at.seconds > 0:
            completed_at = datetime.fromtimestamp(
                response.completed_at.seconds
            ).isoformat()

        return {
            "archive_id": response.archive_id,
            "status": response.status,
            "records_archived": response.records_archived,
            "s3_path": response.s3_path,
            "error_message": response.error_message,
            "created_at": created_at,
            "completed_at": completed_at,
        }
    except Exception as e:
        logger.error(f"Error in get_archive_status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ====================================================================
# Archival Scheduler Management Endpoints (Admin Only)
# ====================================================================

@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: UserContext = Depends(require_auth),
):
    """
    Get archival scheduler status and job information (admin only).
    Returns current schedule, next run times, and execution history.
    """
    # Check if user has admin role
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Call storage service HTTP API directly
    try:
        storage_http_url = f"http://{settings.storage_service_host}:{settings.storage_service_http_port}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{storage_http_url}/scheduler/status")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error calling storage service scheduler/status: {e}")
        raise HTTPException(status_code=502, detail=f"Storage service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_scheduler_status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/trigger/{job_id}")
async def trigger_archival_job(
    job_id: str,
    current_user: UserContext = Depends(require_auth),
):
    """
    Manually trigger an archival job (admin only).
    
    Valid job_ids:
    - archive_market_data: Archives high-frequency tick data
    - archive_market_candles: Archives OHLCV candle data
    """
    # Check if user has admin role
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate job_id
    valid_jobs = ["archive_market_data", "archive_market_candles"]
    if job_id not in valid_jobs:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid job_id. Must be one of: {', '.join(valid_jobs)}"
        )
    
    # Call storage service HTTP API directly
    try:
        storage_http_url = f"http://{settings.storage_service_host}:{settings.storage_service_http_port}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{storage_http_url}/scheduler/trigger/{job_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error calling storage service scheduler/trigger: {e}")
        raise HTTPException(status_code=502, detail=f"Storage service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in trigger_archival_job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archives/{archive_id}/data")
async def query_archive_data(
    archive_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    symbols: List[str] = Query(None),
    start_time: datetime = Query(None),
    end_time: datetime = Query(None),
    current_user: UserContext = Depends(require_auth),
):
    """Query archive data with pagination and filtering"""
    client = get_storage_client()
    try:
        user_id = current_user.user_id
        roles = current_user.roles

        request = storage_pb2.QueryArchiveDataRequest(
            context=common_pb2.UserContext(user_id=user_id, roles=roles),
            archive_id=archive_id,
            limit=limit,
            offset=offset,
            symbols=symbols or [],
        )
        
        if start_time:
            request.start_time.CopyFrom(
                common_pb2.Timestamp(seconds=int(start_time.timestamp()))
            )
        
        if end_time:
            request.end_time.CopyFrom(
                common_pb2.Timestamp(seconds=int(end_time.timestamp()))
            )

        response = client.QueryArchiveData(request)

        rows = []
        for row in response.rows:
            rows.append(dict(row.values))

        return {
            "rows": rows,
            "column_names": list(response.column_names),
            "total_count": response.total_count,
        }
    except Exception as e:
        logger.error(f"Error in query_archive_data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
