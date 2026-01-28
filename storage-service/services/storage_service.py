"""Storage Business Service"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class StorageBusinessService:
    """Business logic for storage operations"""

    def __init__(
        self,
        s3_repository,
        athena_repository,
        clickhouse_repository,
        postgres_repository,
    ):
        self.s3_repo = s3_repository
        self.athena_repo = athena_repository
        self.clickhouse_repo = clickhouse_repository
        self.postgres_repo = postgres_repository
        logger.info("StorageBusinessService initialized")

    async def archive_data(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        data_type: str,
        symbols: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Archive data from ClickHouse to S3
        """
        archive_id = str(uuid.uuid4())

        # 1. Create job
        await self.postgres_repo.create_archive_job(
            archive_id=archive_id,
            data_type=data_type,
            start_time=start_time,
            end_time=end_time,
            metadata={"tenant_id": tenant_id, "symbols": symbols},
        )

        try:
            await self.postgres_repo.update_archive_job(
                archive_id=archive_id,
                status="running",
                started_at=datetime.utcnow(),
            )

            # 2. Export and Upload
            total_records = 0
            total_size = 0
            s3_prefix = f"{data_type}/year={start_time.year}/month={start_time.month}/day={start_time.day}"

            # Using ClickHouse export_data_range
            async for batch in self.clickhouse_repo.export_data_range(
                data_type=data_type,
                start_time=start_time,
                end_time=end_time,
                symbols=symbols,
            ):
                if not batch:
                    continue

                # Upload batch
                batch_id = str(uuid.uuid4())
                s3_key = f"{s3_prefix}/{archive_id}_{batch_id}.parquet"

                await self.s3_repo.upload_parquet(batch, s3_key)

                total_records += len(batch)

            # 3. Calculate total archive size
            total_size = await self.s3_repo.calculate_archive_size(s3_prefix)

            # 4. Register with Athena
            # Run MSCK REPAIR TABLE to discover new partitions
            # Note: This might be slow if many partitions.
            try:
                await self.athena_repo.execute_query(f"MSCK REPAIR TABLE {data_type}")
            except Exception as e:
                logger.warning(f"Failed to repair table partitions: {e}")

            # 5. Update Job
            await self.postgres_repo.update_archive_job(
                archive_id=archive_id,
                status="completed",
                records_archived=total_records,
                size_bytes=total_size,
                completed_at=datetime.utcnow(),
                s3_path=f"s3://{self.s3_repo.bucket_name}/{s3_prefix}",
            )

            return {
                "archive_id": archive_id,
                "success": True,
                "records_count": total_records,
                "s3_path": f"s3://{self.s3_repo.bucket_name}/{s3_prefix}",
                "message": "Archive job started and completed successfully",
            }

        except Exception as e:
            logger.error(f"Archive failed: {e}", exc_info=True)
            await self.postgres_repo.update_archive_job(
                archive_id=archive_id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.utcnow(),
            )
            raise

    async def query_archive(
        self, tenant_id: str, sql_query: str, max_results: int
    ) -> Dict[str, Any]:
        """
        Query archived data using Athena
        """
        # Basic validation: ensure query starts with SELECT
        if not sql_query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        execution_id = await self.athena_repo.execute_query(sql_query)
        status = await self.athena_repo.wait_for_query(execution_id)

        if status != "SUCCEEDED":
            raise RuntimeError(f"Query failed with status {status}")

        results = await self.athena_repo.get_query_results(execution_id, max_results)
        return results

    async def get_archive_status(self, archive_id: str) -> Dict[str, Any]:
        """Get status of an archive job"""
        job = await self.postgres_repo.get_archive_job(archive_id)
        if not job:
            raise ValueError(f"Archive job {archive_id} not found")
        return job

    async def list_archives(
        self,
        limit: int,
        offset: int,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> List[Dict[str, Any]]:
        """List archive jobs"""
        # TODO: Add date filtering to postgres repo
        return await self.postgres_repo.list_archive_jobs(limit=limit, offset=offset)

    async def query_archive_data(
        self,
        archive_id: str,
        limit: int = 100,
        offset: int = 0,
        symbols: List[str] = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> Dict[str, Any]:
        """
        Query archive data with pagination and filtering.
        
        Args:
            archive_id: Archive job ID to query
            limit: Maximum number of rows to return
            offset: Number of rows to skip for pagination
            symbols: Optional list of symbols to filter
            start_time: Optional start time filter
            end_time: Optional end time filter
        
        Returns:
            Dictionary with rows, column_names, and total_count
        """
        # Get archive metadata
        job = await self.postgres_repo.get_archive_job(archive_id)
        if not job:
            raise ValueError(f"Archive job {archive_id} not found")
        
        if job["status"] != "completed":
            raise ValueError(f"Archive job {archive_id} is not completed (status: {job['status']})")
        
        data_type = job.get("data_type", "market_data")
        
        # Build SQL query
        sql_parts = [f"SELECT * FROM {data_type}"]
        where_clauses = []
        
        # Add symbol filter
        if symbols:
            symbols_str = ", ".join([f"'{s}'" for s in symbols])
            where_clauses.append(f"symbol IN ({symbols_str})")
        
        # Add time filters
        if start_time:
            where_clauses.append(f"timestamp >= TIMESTAMP '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        if end_time:
            where_clauses.append(f"timestamp <= TIMESTAMP '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        if where_clauses:
            sql_parts.append("WHERE " + " AND ".join(where_clauses))
        
        sql_parts.append("ORDER BY timestamp DESC")
        sql_parts.append(f"LIMIT {limit} OFFSET {offset}")
        
        sql_query = " ".join(sql_parts)
        
        logger.info(f"Querying archive {archive_id} with SQL: {sql_query}")
        
        # Execute via Athena
        execution_id = await self.athena_repo.execute_query(sql_query)
        status = await self.athena_repo.wait_for_query(execution_id)
        
        if status != "SUCCEEDED":
            raise RuntimeError(f"Archive query failed with status {status}")
        
        results = await self.athena_repo.get_query_results(execution_id, max_results=limit)
        
        # Add total count (approximate - Athena doesn't support COUNT with OFFSET efficiently)
        results["total_count"] = results["row_count"]
        
        return results
