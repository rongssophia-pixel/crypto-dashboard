"""
Standalone Archival Job Functions
These functions are designed to be pickle-safe for APScheduler's SQLAlchemyJobStore.
They accept only primitive arguments and create their own clients.
"""

import asyncio
import importlib.util
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import boto3

# Setup logging
logger = logging.getLogger(__name__)


async def execute_archival_job(
    data_type: str,
    ttl_hours: int,
    # AWS Config
    aws_endpoint_url: str | None,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    aws_region: str,
    s3_bucket_name: str,
    athena_output_bucket: str,
    athena_database: str,
    athena_workgroup: str,
    # ClickHouse Config
    clickhouse_host: str,
    clickhouse_port: int,
    clickhouse_db: str,
    clickhouse_user: str,
    clickhouse_password: str,
    clickhouse_secure: bool,
    clickhouse_verify: bool,
    # PostgreSQL Config
    postgres_host: str,
    postgres_port: int,
    postgres_db: str,
    postgres_user: str,
    postgres_password: str,
) -> Dict[str, Any]:
    """
    Standalone archival job function that can be pickled by APScheduler.
    
    Creates fresh clients, archives data older than TTL to S3,
    then deletes from ClickHouse.
    
    Args:
        data_type: Type of data to archive (market_data or market_candles)
        ttl_hours: Archive data older than this many hours
        Various config parameters as primitives
    
    Returns:
        Dict with execution results
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    logger.info(
        "Starting archival job: data_type=%s, ttl_hours=%d, cutoff=%s",
        data_type,
        ttl_hours,
        cutoff.isoformat(),
    )
    
    # Import repository classes
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from repositories.athena_repository import AthenaRepository
    from repositories.postgres_repository import PostgresRepository
    from repositories.s3_repository import S3Repository
    
    # Dynamic import of ClickHouseRepository from analytics-service
    ch_repo_path = os.path.join(
        str(project_root),
        "analytics-service/repositories/clickhouse_repository.py",
    )
    spec = importlib.util.spec_from_file_location("analytics_clickhouse_repo", ch_repo_path)
    analytics_clickhouse_repo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analytics_clickhouse_repo)
    ClickHouseRepository = analytics_clickhouse_repo.ClickHouseRepository
    
    # Create fresh clients
    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )
    
    s3_client = session.client("s3", endpoint_url=aws_endpoint_url)
    athena_client = session.client("athena", endpoint_url=aws_endpoint_url)
    
    # Initialize repositories
    s3_repo = S3Repository(s3_client, s3_bucket_name)
    athena_repo = AthenaRepository(
        athena_client,
        athena_database,
        athena_output_bucket,
        athena_workgroup,
    )
    
    clickhouse_repo = ClickHouseRepository(
        host=clickhouse_host,
        port=clickhouse_port,
        database=clickhouse_db,
        user=clickhouse_user,
        password=clickhouse_password,
        secure=clickhouse_secure,
        verify=clickhouse_verify,
    )
    
    postgres_repo = PostgresRepository(
        host=postgres_host,
        port=postgres_port,
        database=postgres_db,
        user=postgres_user,
        password=postgres_password,
    )
    
    try:
        # Connect to ClickHouse
        await clickhouse_repo.connect()
        
        # Step 1: Archive to S3
        archive_id = str(uuid.uuid4())
        start_time = datetime(2020, 1, 1, tzinfo=timezone.utc)  # Very old start time
        
        # Create job in PostgreSQL
        await postgres_repo.create_archive_job(
            archive_id=archive_id,
            data_type=data_type,
            start_time=start_time,
            end_time=cutoff,
            metadata={"tenant_id": "system", "symbols": None, "scheduled": True},
        )
        
        await postgres_repo.update_archive_job(
            archive_id=archive_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        
        # Export and upload data
        total_records = 0
        
        # Group data by time period (hour for market_data, day for others)
        # This reduces file count and improves Athena query performance
        time_grouped_data = {}  # key: (year, month, day, hour), value: list of records
        
        async for batch in clickhouse_repo.export_data_range(
            data_type=data_type,
            start_time=start_time,
            end_time=cutoff,
            symbols=None,  # Archive all symbols
            batch_size=500000,  # Larger batches for efficiency
        ):
            if not batch:
                continue
            
            # Group records by timestamp (hour for market_data, day for others)
            for record in batch:
                record_time = record.get("timestamp")
                if not record_time:
                    continue
                
                # Extract year/month/day/hour from actual data timestamp
                if data_type == "market_data":
                    # Group by hour for high-frequency tick data
                    time_key = (
                        record_time.year,
                        record_time.month,
                        record_time.day,
                        record_time.hour,
                    )
                else:
                    # Group by day for aggregated data (market_candles)
                    time_key = (
                        record_time.year,
                        record_time.month,
                        record_time.day,
                        None,  # No hour for daily grouping
                    )
                
                if time_key not in time_grouped_data:
                    time_grouped_data[time_key] = []
                time_grouped_data[time_key].append(record)
        
        # Upload grouped data to S3 (one file per hour/day)
        logger.info(
            "Archiving %s: %d time periods to upload",
            data_type,
            len(time_grouped_data),
        )
        
        s3_paths = set()
        for time_key, records in time_grouped_data.items():
            year, month, day, hour = time_key
            
            # Create partition path based on actual data timestamps
            if hour is not None:
                # Hourly partitioning for market_data
                s3_prefix = f"{data_type}/year={year}/month={month}/day={day}/hour={hour}"
                s3_key = f"{s3_prefix}/{archive_id}.parquet"
            else:
                # Daily partitioning for market_candles
                s3_prefix = f"{data_type}/year={year}/month={month}/day={day}"
                s3_key = f"{s3_prefix}/{archive_id}.parquet"
            
            await s3_repo.upload_parquet(records, s3_key)
            total_records += len(records)
            s3_paths.add(f"s3://{s3_bucket_name}/{s3_prefix}")
        
        logger.info(
            "Uploaded %d records across %d time periods for %s",
            total_records,
            len(time_grouped_data),
            data_type,
        )
        
        # Register with Athena (optional, may fail)
        try:
            await athena_repo.execute_query(f"MSCK REPAIR TABLE {data_type}")
        except Exception as e:
            logger.warning(f"Failed to repair table partitions: {e}")
        
        # Update job status
        s3_path = f"s3://{s3_bucket_name}/{data_type}/ (multiple partitions)"
        await postgres_repo.update_archive_job(
            archive_id=archive_id,
            status="completed",
            records_archived=total_records,
            completed_at=datetime.now(timezone.utc),
            s3_path=s3_path,
        )
        
        if total_records == 0:
            logger.info("No data to archive for %s before %s", data_type, cutoff)
            return {
                "success": True,
                "data_type": data_type,
                "records_archived": 0,
                "records_deleted": 0,
                "message": "No data to archive",
            }
        
        logger.info(
            "Archived %d records for %s across %d partitions",
            total_records,
            data_type,
            len(s3_paths),
        )
        
        # Step 2: Delete archived data from ClickHouse
        deleted_count = await clickhouse_repo.delete_data_before(
            data_type=data_type,
            cutoff_time=cutoff,
        )
        
        logger.info(
            "Deleted %d records from ClickHouse for %s",
            deleted_count,
            data_type,
        )
        
        return {
            "success": True,
            "data_type": data_type,
            "records_archived": total_records,
            "records_deleted": deleted_count,
            "s3_path": s3_path,
            "s3_partitions": len(s3_paths),
            "archive_id": archive_id,
        }
        
    except Exception as e:
        logger.error(
            "Error in archival job for %s: %s",
            data_type,
            e,
            exc_info=True,
        )
        
        # Update job to failed if archive_id exists
        try:
            if 'archive_id' in locals():
                await postgres_repo.update_archive_job(
                    archive_id=archive_id,
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc),
                )
        except Exception:
            pass
        
        raise
    
    finally:
        # Cleanup connections
        try:
            await clickhouse_repo.close()
        except Exception as e:
            logger.warning(f"Error closing ClickHouse connection: {e}")

