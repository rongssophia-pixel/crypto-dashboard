"""Notification Repository"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg

logger = logging.getLogger(__name__)


class NotificationRepository:
    """Repository for notification log operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        logger.info("NotificationRepository initialized")
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: str,
        subject: str,
        body: str,
        recipients: List[str],
        priority: str
    ) -> Dict[str, Any]:
        """Create notification record"""
        query = """
            INSERT INTO notification_logs 
                (user_id, notification_type, subject, body, recipients, priority, status, retry_count)
            VALUES ($1, $2, $3, $4, $5, $6, 'pending', 0)
            RETURNING id, user_id, notification_type, subject, status, priority, created_at
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    user_id,
                    notification_type,
                    subject,
                    body,
                    recipients,
                    priority
                )
                result = dict(row)
                logger.info(f"Created notification {result['id']} for user {user_id}")
                return result
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            raise
    
    async def update_status(
        self,
        notification_id: str,
        status: str,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None
    ) -> bool:
        """Update notification status"""
        query = """
            UPDATE notification_logs
            SET status = $2,
                error_message = $3,
                sent_at = COALESCE($4, sent_at),
                delivered_at = CASE WHEN $2 = 'delivered' THEN CURRENT_TIMESTAMP ELSE delivered_at END
            WHERE id = $1
            RETURNING id
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, notification_id, status, error_message, sent_at)
                if row:
                    logger.info(f"Updated notification {notification_id} status to {status}")
                    return True
                else:
                    logger.warning(f"Notification {notification_id} not found for status update")
                    return False
        except Exception as e:
            logger.error(f"Failed to update notification status: {e}")
            raise
    
    async def get_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Get notification by ID"""
        query = """
            SELECT id, user_id, notification_type, subject, body, recipients,
                   status, error_message, retry_count, priority,
                   created_at, sent_at, delivered_at, metadata
            FROM notification_logs
            WHERE id = $1
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, notification_id)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Failed to get notification {notification_id}: {e}")
            raise
    
    async def get_user_history(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """Get notification history for user"""
        query = """
            SELECT id, notification_type, subject, status, 
                   created_at, sent_at, priority
            FROM notification_logs
            WHERE user_id = $1
              AND created_at >= $2
              AND created_at <= $3
            ORDER BY created_at DESC
            LIMIT $4 OFFSET $5
        """
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, user_id, start_time, end_time, limit, offset)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get user history for {user_id}: {e}")
            raise
    
    async def get_failed_notifications_for_retry(self, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Get failed notifications eligible for retry"""
        query = """
            SELECT id, user_id, notification_type, subject, body, recipients, 
                   priority, retry_count, created_at, error_message
            FROM notification_logs
            WHERE status = 'failed'
              AND retry_count < $1
            ORDER BY created_at ASC
            LIMIT 100
        """
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, max_retries)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get failed notifications: {e}")
            raise
    
    async def increment_retry_count(self, notification_id: str) -> bool:
        """Increment retry count for a notification"""
        query = """
            UPDATE notification_logs
            SET retry_count = retry_count + 1
            WHERE id = $1
            RETURNING id
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, notification_id)
                return row is not None
        except Exception as e:
            logger.error(f"Failed to increment retry count: {e}")
            raise
    
    async def get_user_email(self, user_id: str) -> Optional[str]:
        """Get user email from users table"""
        query = "SELECT email FROM users WHERE id = $1"
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, user_id)
                if row:
                    return row['email']
                return None
        except Exception as e:
            logger.error(f"Failed to get user email for {user_id}: {e}")
            raise
