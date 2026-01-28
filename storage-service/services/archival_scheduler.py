"""
Archival Scheduler Service
Automatically archives data from ClickHouse to S3 based on TTL configuration,
then deletes the archived data from ClickHouse.

Uses APScheduler with PostgreSQL job store for persistence.
Jobs survive service restarts.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services.archival_jobs import execute_archival_job

logger = logging.getLogger(__name__)


class ArchivalScheduler:
    """
    Scheduler for automatic data archival from ClickHouse (hot) to S3 (cold).
    Uses APScheduler with PostgreSQL job store for persistence.
    Jobs survive service restarts.
    """

    def __init__(
        self,
        database_url: str,
        market_data_ttl_hours: int,
        market_candles_ttl_hours: int,
        market_data_cron: str,
        market_candles_cron: str,
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
    ):
        """
        Initialize the archival scheduler with PostgreSQL job store.

        Args:
            database_url: PostgreSQL connection string for job store
            market_data_ttl_hours: Archive market_data older than this
            market_candles_ttl_hours: Archive market_candles older than this
            market_data_cron: Cron expression for market_data archival
            market_candles_cron: Cron expression for market_candles archival
            ... various config parameters as primitives
        """
        self.market_data_ttl_hours = market_data_ttl_hours
        self.market_candles_ttl_hours = market_candles_ttl_hours
        self.market_data_cron = market_data_cron
        self.market_candles_cron = market_candles_cron
        
        # Store config for passing to jobs
        self.config = {
            "aws_endpoint_url": aws_endpoint_url,
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "aws_region": aws_region,
            "s3_bucket_name": s3_bucket_name,
            "athena_output_bucket": athena_output_bucket,
            "athena_database": athena_database,
            "athena_workgroup": athena_workgroup,
            "clickhouse_host": clickhouse_host,
            "clickhouse_port": clickhouse_port,
            "clickhouse_db": clickhouse_db,
            "clickhouse_user": clickhouse_user,
            "clickhouse_password": clickhouse_password,
            "clickhouse_secure": clickhouse_secure,
            "clickhouse_verify": clickhouse_verify,
            "postgres_host": postgres_host,
            "postgres_port": postgres_port,
            "postgres_db": postgres_db,
            "postgres_user": postgres_user,
            "postgres_password": postgres_password,
        }

        # Job execution stats (in-memory, for status endpoint)
        self._stats = {
            "market_data": {"last_run": None, "last_status": None, "records_archived": 0},
            "market_candles": {"last_run": None, "last_status": None, "records_archived": 0},
        }

        # Configure SQLAlchemy job store
        jobstores = {
            "default": SQLAlchemyJobStore(url=database_url)
        }

        # Create scheduler with PostgreSQL persistence
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            job_defaults={
                "coalesce": True,  # Combine multiple missed runs into one
                "max_instances": 1,  # Prevent overlapping runs of the same job
                "misfire_grace_time": 3600,  # 1 hour grace period for missed jobs
            },
        )

        # Add event listeners for monitoring
        self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

        logger.info(
            "ArchivalScheduler initialized with PostgreSQL job store: "
            "market_data_ttl=%dh (cron: %s), market_candles_ttl=%dh (cron: %s)",
            market_data_ttl_hours,
            market_data_cron,
            market_candles_ttl_hours,
            market_candles_cron,
        )

    def _on_job_executed(self, event):
        """Handler for successful job execution"""
        logger.info("Archival job '%s' executed successfully", event.job_id)
        
        # Update stats based on job_id
        if "market_data" in event.job_id:
            self._stats["market_data"]["last_run"] = datetime.now(timezone.utc)
            self._stats["market_data"]["last_status"] = "success"
        elif "market_candles" in event.job_id:
            self._stats["market_candles"]["last_run"] = datetime.now(timezone.utc)
            self._stats["market_candles"]["last_status"] = "success"

    def _on_job_error(self, event):
        """Handler for job execution errors"""
        logger.error(
            "Archival job '%s' failed with exception: %s",
            event.job_id,
            event.exception,
            exc_info=True,
        )
        
        # Update stats based on job_id
        if "market_data" in event.job_id:
            self._stats["market_data"]["last_run"] = datetime.now(timezone.utc)
            self._stats["market_data"]["last_status"] = "error"
        elif "market_candles" in event.job_id:
            self._stats["market_candles"]["last_run"] = datetime.now(timezone.utc)
            self._stats["market_candles"]["last_status"] = "error"

    def start(self):
        """Start the archival scheduler with configured cron jobs"""
        # Parse cron expressions
        # Format: "minute hour day month day_of_week"
        # Example: "0 * * * *" = every hour at minute 0
        
        # Parse market_data cron
        md_parts = self.market_data_cron.split()
        if len(md_parts) != 5:
            raise ValueError(
                f"Invalid cron expression for market_data: {self.market_data_cron}"
            )
        
        # Parse market_candles cron
        mc_parts = self.market_candles_cron.split()
        if len(mc_parts) != 5:
            raise ValueError(
                f"Invalid cron expression for market_candles: {self.market_candles_cron}"
            )
        
        # Job 1: Archive market_data (high frequency tick data, short TTL)
        # Use replace_existing=True to handle jobs persisted from previous runs
        logger.info("Adding/updating job: archive_market_data")
        self.scheduler.add_job(
            execute_archival_job,
            CronTrigger(
                minute=md_parts[0],
                hour=md_parts[1],
                day=md_parts[2],
                month=md_parts[3],
                day_of_week=md_parts[4],
            ),
            id="archive_market_data",
            name="Archive market_data to S3",
            replace_existing=True,  # Replace if exists from previous run
            kwargs={
                "data_type": "market_data",
                "ttl_hours": self.market_data_ttl_hours,
                **self.config,
            },
        )

        # Job 2: Archive market_candles (aggregated data, longer TTL)
        logger.info("Adding/updating job: archive_market_candles")
        self.scheduler.add_job(
            execute_archival_job,
            CronTrigger(
                minute=mc_parts[0],
                hour=mc_parts[1],
                day=mc_parts[2],
                month=mc_parts[3],
                day_of_week=mc_parts[4],
            ),
            id="archive_market_candles",
            name="Archive market_candles to S3",
            replace_existing=True,  # Replace if exists from previous run
            kwargs={
                "data_type": "market_candles",
                "ttl_hours": self.market_candles_ttl_hours,
                **self.config,
            },
        )

        self.scheduler.start()
        logger.info(
            "ArchivalScheduler started with %d jobs (persisted in PostgreSQL)",
            len(self.scheduler.get_jobs())
        )

    def stop(self):
        """Stop the archival scheduler gracefully"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("ArchivalScheduler stopped (jobs remain in PostgreSQL)")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status and job information"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                    "trigger": str(job.trigger),
                }
            )

        # Format stats with consistent timezone-aware ISO strings
        formatted_stats = {}
        for data_type, stat in self._stats.items():
            formatted_stats[data_type] = {
                "last_run": stat["last_run"].isoformat() if stat["last_run"] else None,
                "last_status": stat["last_status"],
                "records_archived": stat["records_archived"],
            }

        return {
            "enabled": True,
            "running": self.scheduler.running,
            "job_store": "PostgreSQL (SQLAlchemyJobStore)",
            "persistence": "enabled",
            "jobs": jobs,
            "config": {
                "market_data_ttl_hours": self.market_data_ttl_hours,
                "market_data_cron": self.market_data_cron,
                "market_candles_ttl_hours": self.market_candles_ttl_hours,
                "market_candles_cron": self.market_candles_cron,
            },
            "stats": formatted_stats,
        }

    async def trigger_job(self, job_id: str) -> bool:
        """
        Manually trigger a specific archival job (useful for testing/admin).

        Args:
            job_id: Job identifier (archive_market_data or archive_market_candles)

        Returns:
            True if job was triggered, False if job not found
        """
        job = self.scheduler.get_job(job_id)
        if not job:
            logger.warning("Job not found: %s", job_id)
            return False

        # Trigger the job by modifying next_run_time to now
        job.modify(next_run_time=datetime.now(timezone.utc))
        logger.info("Job '%s' triggered manually", job_id)
        return True
