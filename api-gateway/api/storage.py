"""
Storage API Endpoints
Proxy to Storage Service via gRPC
"""

import logging
from datetime import datetime
from typing import List

from config import settings
from fastapi import APIRouter, Depends, HTTPException, Query
from middleware.auth_middleware import verify_token

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
    token: dict = Depends(verify_token),
):
    """Trigger archive job"""
    client = get_storage_client()
    try:
        user_id = token.get("sub")
        roles = token.get("roles", [])

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
    token: dict = Depends(verify_token),
):
    """Query archived data"""
    client = get_storage_client()
    try:
        user_id = token.get("sub")
        roles = token.get("roles", [])

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
    token: dict = Depends(verify_token),
):
    """List archives"""
    client = get_storage_client()
    try:
        user_id = token.get("sub")
        roles = token.get("roles", [])

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
    token: dict = Depends(verify_token),
):
    """Get archive status"""
    client = get_storage_client()
    try:
        user_id = token.get("sub")
        roles = token.get("roles", [])

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
