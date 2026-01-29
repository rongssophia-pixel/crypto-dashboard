"""
Standalone Archival Job Functions
These functions are designed to be pickle-safe for APScheduler's SQLAlchemyJobStore.
They accept only primitive arguments and create their own clients.
"""

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


async def execute_archival_job(  # noqa: C901
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
    spec = importlib.util.spec_from_file_location(
        "analytics_clickhouse_repo", ch_repo_path
    )
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

        # Export and upload data with timestamp tracking
        total_records = 0
        data_min_timestamp = None
        data_max_timestamp = None
        s3_paths_set = set()

        async for batch in clickhouse_repo.export_data_range(
            data_type=data_type,
            start_time=start_time,
            end_time=cutoff,
            symbols=None,  # Archive all symbols
        ):
            if not batch:
                continue

            # Extract timestamp from first row to track min/max
            first_row_timestamp = batch[0].get("timestamp")
            last_row_timestamp = batch[-1].get("timestamp")

            if first_row_timestamp:
                if (
                    data_min_timestamp is None
                    or first_row_timestamp < data_min_timestamp
                ):
                    data_min_timestamp = first_row_timestamp

            if last_row_timestamp:
                if (
                    data_max_timestamp is None
                    or last_row_timestamp > data_max_timestamp
                ):
                    data_max_timestamp = last_row_timestamp

            # Add archive_id to each row for filtering in Athena
            for row in batch:
                row["archive_id"] = archive_id

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
                logger.warning(
                    "No timestamp in batch, using job start_time for partitioning"
                )
                s3_prefix = (
                    f"{data_type}/"
                    f"year={start_time.year}/"
                    f"month={start_time.month:02d}/"
                    f"day={start_time.day:02d}/"
                    f"hour={start_time.hour:02d}"
                )
                s3_paths_set.add(s3_prefix)

            # Upload batch to S3
            batch_id = str(uuid.uuid4())
            s3_key = f"{s3_prefix}/{archive_id}_{batch_id}.parquet"

            await s3_repo.upload_parquet(batch, s3_key)
            total_records += len(batch)

        # Calculate total archive size across all paths
        total_size = 0
        for s3_path_prefix in s3_paths_set:
            size = await s3_repo.calculate_archive_size(s3_path_prefix)
            total_size += size

        # Register with Athena (optional, may fail)
        try:
            await athena_repo.execute_query(f"MSCK REPAIR TABLE {data_type}")
        except Exception as e:
            logger.warning(f"Failed to repair table partitions: {e}")

        # Update job status with actual data timestamps and paths
        primary_s3_path = (
            f"s3://{s3_bucket_name}/{list(s3_paths_set)[0]}" if s3_paths_set else None
        )

        await postgres_repo.update_archive_job(
            archive_id=archive_id,
            status="completed",
            records_archived=total_records,
            size_bytes=total_size,
            completed_at=datetime.now(timezone.utc),
            s3_path=primary_s3_path,
            data_min_timestamp=data_min_timestamp,
            data_max_timestamp=data_max_timestamp,
            s3_paths=list(s3_paths_set),
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
            "Archived %d records for %s to %s",
            total_records,
            data_type,
            primary_s3_path,
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
            "s3_path": primary_s3_path,
            "archive_id": archive_id,
            "data_min_timestamp": (
                data_min_timestamp.isoformat() if data_min_timestamp else None
            ),
            "data_max_timestamp": (
                data_max_timestamp.isoformat() if data_max_timestamp else None
            ),
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
            if "archive_id" in locals():
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
            await clickhouse_repo.disconnect()
        except Exception as e:
            logger.warning("Error closing ClickHouse connection: %s", e)
