"""
Stream Repository
Handles database operations for stream sessions
"""

import logging
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger(__name__)


class StreamRepository:
    """Repository for stream session persistence"""

    def __init__(self, connection_pool: SimpleConnectionPool):
        self.pool = connection_pool
        logger.info("StreamRepository initialized")

    def _get_connection(self):
        """Get a connection from the pool"""
        return self.pool.getconn()

    def _release_connection(self, conn):
        """Release a connection back to the pool"""
        self.pool.putconn(conn)

    async def create_stream(
        self,
        tenant_id: str,
        stream_id: str,
        symbols: List[str],
        exchange: str,
        stream_type: str,
    ) -> Dict[str, Any]:
        """Create a new stream session record"""
        conn = self._get_connection()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO stream_sessions (
                        tenant_id, stream_id, symbols, exchange, stream_type, status, started_at
                    ) VALUES (%s, %s, %s, %s, %s, 'active', CURRENT_TIMESTAMP)
                    RETURNING *
                """,
                    (tenant_id, stream_id, symbols, exchange, stream_type),
                )

                conn.commit()
                record = cursor.fetchone()
                logger.info(f"Created stream session: {stream_id}")
                return dict(record)

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create stream: {e}")
            raise
        finally:
            self._release_connection(conn)

    async def get_stream(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get stream session by ID"""
        conn = self._get_connection()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM stream_sessions WHERE stream_id = %s
                """,
                    (stream_id,),
                )

                record = cursor.fetchone()
                return dict(record) if record else None

        finally:
            self._release_connection(conn)

    async def update_stream_status(
        self, stream_id: str, status: str, error_message: Optional[str] = None
    ) -> bool:
        """Update stream status"""
        conn = self._get_connection()

        try:
            with conn.cursor() as cursor:
                if error_message:
                    cursor.execute(
                        """
                        UPDATE stream_sessions
                        SET status = %s, error_message = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE stream_id = %s
                    """,
                        (status, error_message, stream_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE stream_sessions
                        SET status = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE stream_id = %s
                    """,
                        (status, stream_id),
                    )

                conn.commit()
                logger.info(f"Updated stream status: {stream_id} -> {status}")
                return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update stream status: {e}")
            return False
        finally:
            self._release_connection(conn)

    async def increment_event_count(self, stream_id: str, count: int = 1) -> bool:
        """Increment events processed counter"""
        conn = self._get_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE stream_sessions
                    SET events_processed = events_processed + %s,
                        last_event_at = CURRENT_TIMESTAMP
                    WHERE stream_id = %s
                """,
                    (count, stream_id),
                )

                conn.commit()
                return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to increment event count: {e}")
            return False
        finally:
            self._release_connection(conn)

    async def list_active_streams(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List all active streams for a tenant"""
        conn = self._get_connection()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM stream_sessions
                    WHERE tenant_id = %s AND status = 'active'
                    ORDER BY started_at DESC
                """,
                    (tenant_id,),
                )

                records = cursor.fetchall()
                return [dict(r) for r in records]

        finally:
            self._release_connection(conn)

    async def stop_stream(self, stream_id: str) -> bool:
        """Mark stream as stopped"""
        conn = self._get_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE stream_sessions
                    SET status = 'stopped', stopped_at = CURRENT_TIMESTAMP
                    WHERE stream_id = %s
                """,
                    (stream_id,),
                )

                conn.commit()
                logger.info(f"Stopped stream: {stream_id}")
                return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to stop stream: {e}")
            return False
        finally:
            self._release_connection(conn)


# TODO: Add error handling
# TODO: Add transaction management
# TODO: Add query optimization
# TODO: Add multi-tenancy filtering
