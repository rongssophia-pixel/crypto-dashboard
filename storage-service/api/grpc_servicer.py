"""Storage Service gRPC Servicer"""

import logging
from datetime import datetime

import grpc

from proto import common_pb2, storage_pb2, storage_pb2_grpc

logger = logging.getLogger(__name__)


class StorageServiceServicer(storage_pb2_grpc.StorageServiceServicer):
    """gRPC servicer for Storage Service"""

    def __init__(self, business_service):
        self.business_service = business_service
        logger.info("StorageServiceServicer initialized")

    def _get_datetime(self, proto_ts):
        """Convert proto timestamp to datetime"""
        if not proto_ts or proto_ts.seconds == 0:
            return datetime.utcnow()  # Default or error?
        return datetime.fromtimestamp(proto_ts.seconds + proto_ts.nanos / 1e9)

    def _to_proto_timestamp(self, dt):
        """Convert datetime to proto timestamp"""
        if not dt:
            return common_pb2.Timestamp()
        return common_pb2.Timestamp(
            seconds=int(dt.timestamp()), nanos=int(dt.microsecond * 1000)
        )

    async def ArchiveData(self, request, context):
        """Archive data to S3"""
        try:
            start_time = self._get_datetime(request.start_time)
            end_time = self._get_datetime(request.end_time)

            result = await self.business_service.archive_data(
                tenant_id=request.context.user_id,  # Assuming context has user_id
                start_time=start_time,
                end_time=end_time,
                data_type=request.data_type,
                symbols=list(request.symbols),
            )

            return storage_pb2.ArchiveResponse(
                archive_id=result["archive_id"],
                success=result["success"],
                s3_path=result.get("s3_path", ""),
                message=result.get("message", ""),
                records_count=result.get("records_count", 0),
            )
        except Exception as e:
            logger.error(f"ArchiveData failed: {e}")
            return storage_pb2.ArchiveResponse(success=False, message=str(e))

    async def QueryArchive(self, request, context):
        """Query archived data using Athena"""
        try:
            result = await self.business_service.query_archive(
                tenant_id=request.context.user_id,
                sql_query=request.sql_query,
                max_results=request.max_results,
            )

            rows = []
            for row_data in result["rows"]:
                # ArchiveRow map<string, string> values = 1;
                # Convert all values to string for simplicity
                values_str = {k: str(v) for k, v in row_data.items()}
                rows.append(storage_pb2.ArchiveRow(values=values_str))

            return storage_pb2.ArchiveQueryResponse(
                rows=rows,
                column_names=result["column_names"],
                row_count=result["row_count"],
                execution_id=result["execution_id"],
            )
        except Exception as e:
            logger.error(f"QueryArchive failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return storage_pb2.ArchiveQueryResponse()

    async def GetArchiveStatus(self, request, context):
        """Get status of archival job"""
        try:
            job = await self.business_service.get_archive_status(request.archive_id)

            return storage_pb2.ArchiveStatusResponse(
                archive_id=job["archive_id"],
                status=job["status"],
                records_archived=job.get("records_archived", 0),
                s3_path=job.get("s3_path", ""),
                error_message=job.get("error_message", ""),
                created_at=self._to_proto_timestamp(job.get("created_at")),
                completed_at=self._to_proto_timestamp(job.get("completed_at")),
            )
        except Exception as e:
            logger.error(f"GetArchiveStatus failed: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return storage_pb2.ArchiveStatusResponse()

    async def ListArchives(self, request, context):
        """List available archives"""
        try:
            jobs = await self.business_service.list_archives(
                limit=request.limit or 20, offset=request.offset or 0
            )

            archives = []
            for job in jobs:
                archives.append(
                    storage_pb2.ArchiveMetadata(
                        archive_id=job["archive_id"],
                        s3_path=job.get("s3_path", ""),
                        created_at=self._to_proto_timestamp(job.get("created_at")),
                        size_bytes=job.get("size_bytes", 0),
                        records_count=job.get("records_archived", 0),
                        data_type=job.get("data_type", ""),
                        status=job.get("status", "pending"),
                    )
                )

            return storage_pb2.ListArchivesResponse(
                archives=archives,
                total_count=len(archives),  # Approximate for now
            )
        except Exception as e:
            logger.error(f"ListArchives failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return storage_pb2.ListArchivesResponse()

    async def QueryArchiveData(self, request, context):
        """Query specific archive data with pagination and filtering"""
        try:
            start_time = None
            if request.start_time and request.start_time.seconds > 0:
                start_time = self._get_datetime(request.start_time)
            
            end_time = None
            if request.end_time and request.end_time.seconds > 0:
                end_time = self._get_datetime(request.end_time)

            result = await self.business_service.query_archive_data(
                archive_id=request.archive_id,
                limit=request.limit or 100,
                offset=request.offset or 0,
                symbols=list(request.symbols) if request.symbols else None,
                start_time=start_time,
                end_time=end_time,
            )

            rows = []
            for row_data in result["rows"]:
                # Convert all values to string for simplicity
                values_str = {k: str(v) for k, v in row_data.items()}
                rows.append(storage_pb2.ArchiveRow(values=values_str))

            return storage_pb2.QueryArchiveDataResponse(
                rows=rows,
                column_names=result["column_names"],
                total_count=result.get("total_count", result["row_count"]),
            )
        except Exception as e:
            logger.error(f"QueryArchiveData failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return storage_pb2.QueryArchiveDataResponse()
