"""PostgreSQL Repository for Archive Jobs"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


class PostgresRepository:
    """Repository for PostgreSQL operations."""

    def __init__(self, host, port, database, user, password):
        self.dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.pool = None

    async def connect(self):
        """Create connection pool."""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(self.dsn)
                logger.info("Connected to PostgreSQL")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL")

    async def create_archive_job(
        self,
        archive_id: str,
        data_type: str,
        start_time: datetime,
        end_time: datetime,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Create a new archive job record."""
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO archive_jobs (
                archive_id, data_type, start_time, end_time, status, metadata
            ) VALUES (
                $1, $2, $3, $4, 'pending', $5
            ) RETURNING id
        """

        try:
            row = await self.pool.fetchrow(
                query,
                archive_id,
                data_type,
                start_time,
                end_time,
                json.dumps(metadata) if metadata else "{}",
            )
            return str(row["id"])
        except Exception as e:
            logger.error(f"Failed to create archive job: {e}")
            raise

    async def update_archive_job(
        self,
        archive_id: str,
        status: str = None,
        s3_path: str = None,
        records_archived: int = None,
        size_bytes: int = None,
        error_message: str = None,
        completed_at: datetime = None,
        started_at: datetime = None,
    ) -> bool:
        """Update archive job status and details."""
        if not self.pool:
            await self.connect()

        # Build dynamic update query
        updates = []
        values = []
        idx = 1

        if status is not None:
            updates.append(f"status = ${idx}")
            values.append(status)
            idx += 1

        if s3_path is not None:
            updates.append(f"s3_path = ${idx}")
            values.append(s3_path)
            idx += 1

        if records_archived is not None:
            updates.append(f"records_archived = ${idx}")
            values.append(records_archived)
            idx += 1

        if size_bytes is not None:
            updates.append(f"size_bytes = ${idx}")
            values.append(size_bytes)
            idx += 1

        if error_message is not None:
            updates.append(f"error_message = ${idx}")
            values.append(error_message)
            idx += 1

        if completed_at is not None:
            updates.append(f"completed_at = ${idx}")
            values.append(completed_at)
            idx += 1

        if started_at is not None:
            updates.append(f"started_at = ${idx}")
            values.append(started_at)
            idx += 1

        if not updates:
            return False

        values.append(archive_id)
        query = f"""
            UPDATE archive_jobs
            SET {', '.join(updates)}
            WHERE archive_id = ${idx}
        """

        try:
            result = await self.pool.execute(query, *values)
            return result != "UPDATE 0"
        except Exception as e:
            logger.error(f"Failed to update archive job {archive_id}: {e}")
            raise

    async def get_archive_job(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """Get archive job details."""
        if not self.pool:
            await self.connect()

        query = "SELECT * FROM archive_jobs WHERE archive_id = $1"

        try:
            row = await self.pool.fetchrow(query, archive_id)
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get archive job {archive_id}: {e}")
            raise

    async def list_archive_jobs(
        self, limit: int = 20, offset: int = 0, status: str = None
    ) -> List[Dict[str, Any]]:
        """List archive jobs with optional filtering."""
        if not self.pool:
            await self.connect()

        query = "SELECT * FROM archive_jobs"
        values = []
        idx = 1

        if status:
            query += f" WHERE status = ${idx}"
            values.append(status)
            idx += 1

        query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx+1}"
        values.extend([limit, offset])

        try:
            rows = await self.pool.fetch(query, *values)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list archive jobs: {e}")
            raise
