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
        Archive data from ClickHouse to S3 with hourly partitioning
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

            # 2. Export and Upload with timestamp tracking
            total_records = 0
            data_min_timestamp = None
            data_max_timestamp = None
            s3_paths_set = set()

            # Using ClickHouse export_data_range
            async for batch in self.clickhouse_repo.export_data_range(
                data_type=data_type,
                start_time=start_time,
                end_time=end_time,
                symbols=symbols,
            ):
                if not batch:
                    continue

                # Extract timestamp from first row to track min/max
                first_row_timestamp = batch[0].get('timestamp')
                last_row_timestamp = batch[-1].get('timestamp')
                
                if first_row_timestamp:
                    if data_min_timestamp is None or first_row_timestamp < data_min_timestamp:
                        data_min_timestamp = first_row_timestamp
                
                if last_row_timestamp:
                    if data_max_timestamp is None or last_row_timestamp > data_max_timestamp:
                        data_max_timestamp = last_row_timestamp

                # Add archive_id to each row for filtering in Athena
                for row in batch:
                    row['archive_id'] = archive_id

                # Generate S3 path based on actual data timestamp (hourly partitions)
                if first_row_timestamp:
                    s3_prefix = (
                        f"{data_type}/"
                        f"year={first_row_timestamp.year}/"
                        f"month={first_row_timestamp.month:02d}/"
                        f"day={first_row_timestamp.day:02d}/"
                        f"hour={first_row_timestamp.hour:02d}"
                    )
                    s3_paths_set.add(s3_prefix)
                else:
                    # Fallback to job start_time if timestamp not available
                    logger.warning(f"No timestamp in batch, using job start_time for partitioning")
                    s3_prefix = (
                        f"{data_type}/"
                        f"year={start_time.year}/"
                        f"month={start_time.month:02d}/"
                        f"day={start_time.day:02d}/"
                        f"hour={start_time.hour:02d}"
                    )
                    s3_paths_set.add(s3_prefix)

                # Upload batch
                batch_id = str(uuid.uuid4())
                s3_key = f"{s3_prefix}/{archive_id}_{batch_id}.parquet"

                await self.s3_repo.upload_parquet(batch, s3_key)
                total_records += len(batch)

            # 3. Calculate total archive size across all paths
            total_size = 0
            for s3_path in s3_paths_set:
                size = await self.s3_repo.calculate_archive_size(s3_path)
                total_size += size

            # 4. Register with Athena
            # Run MSCK REPAIR TABLE to discover new hourly partitions
            try:
                await self.athena_repo.execute_query(f"MSCK REPAIR TABLE {data_type}")
            except Exception as e:
                logger.warning(f"Failed to repair table partitions: {e}")

            # 5. Update Job with actual data timestamps and paths
            primary_s3_path = f"s3://{self.s3_repo.bucket_name}/{list(s3_paths_set)[0]}" if s3_paths_set else None
            
            await self.postgres_repo.update_archive_job(
                archive_id=archive_id,
                status="completed",
                records_archived=total_records,
                size_bytes=total_size,
                completed_at=datetime.utcnow(),
                s3_path=primary_s3_path,
                data_min_timestamp=data_min_timestamp,
                data_max_timestamp=data_max_timestamp,
                s3_paths=list(s3_paths_set),
            )

            return {
                "archive_id": archive_id,
                "success": True,
                "records_count": total_records,
                "s3_path": primary_s3_path,
                "data_min_timestamp": data_min_timestamp.isoformat() if data_min_timestamp else None,
                "data_max_timestamp": data_max_timestamp.isoformat() if data_max_timestamp else None,
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
        
        Now filters by archive_id to ensure only data from this specific
        archive job is returned.
        
        Note: Athena doesn't support OFFSET, so pagination is limited.
        The offset parameter is accepted but ignored for Athena compatibility.
        
        Args:
            archive_id: Archive job ID to query
            limit: Maximum number of rows to return
            offset: Number of rows to skip (not supported by Athena, ignored)
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
        
        # Build SQL query (Athena/Presto doesn't support OFFSET)
        sql_parts = [f"SELECT * FROM {data_type}"]
        where_clauses = []
        
        # CRITICAL: Filter by archive_id to get only this job's data
        where_clauses.append(f"archive_id = '{archive_id}'")
        
        # Add symbol filter
        if symbols:
            symbols_str = ", ".join([f"'{s}'" for s in symbols])
            where_clauses.append(f"symbol IN ({symbols_str})")
        
        # Add time filters (optional, archive_id already isolates the data)
        if start_time:
            where_clauses.append(f"timestamp >= TIMESTAMP '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        if end_time:
            where_clauses.append(f"timestamp <= TIMESTAMP '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        sql_parts.append("WHERE " + " AND ".join(where_clauses))
        sql_parts.append("ORDER BY timestamp DESC")
        sql_parts.append(f"LIMIT {limit}")
        # Note: OFFSET not supported by Athena, pagination limited to LIMIT only
        
        sql_query = " ".join(sql_parts)
        
        logger.info(f"Querying archive {archive_id} with SQL: {sql_query}")
        
        # Execute via Athena
        try:
            execution_id = await self.athena_repo.execute_query(sql_query)
            status = await self.athena_repo.wait_for_query(execution_id)
            
            if status != "SUCCEEDED":
                # Try to get error details from Athena
                error_msg = f"Archive query failed with status {status}"
                try:
                    import asyncio
                    response = await asyncio.to_thread(
                        self.athena_repo.athena.get_query_execution,
                        QueryExecutionId=execution_id
                    )
                    error_details = response.get("QueryExecution", {}).get("Status", {}).get("StateChangeReason", "")
                    if error_details:
                        error_msg += f": {error_details}"
                    logger.error(f"Athena query failed: {error_msg}")
                except Exception as e:
                    logger.warning(f"Could not get Athena error details: {e}")
                raise RuntimeError(error_msg)
            
            results = await self.athena_repo.get_query_results(execution_id, max_results=limit)
        except Exception as e:
            logger.error(f"Error executing Athena query for archive {archive_id}: {e}", exc_info=True)
            raise
        
        # Add total count
        results["total_count"] = results["row_count"]
        
        return results
