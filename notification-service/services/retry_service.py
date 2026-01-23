"""
Retry Service
Handles automatic retry of failed notifications with exponential backoff
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class RetryService:
    """
    Background service that retries failed notifications
    Uses exponential backoff: delay = 2^retry_count * base_interval
    """
    
    def __init__(
        self,
        notification_repo,
        business_service,
        max_retries: int = 3,
        check_interval: int = 60
    ):
        """
        Initialize retry service
        
        Args:
            notification_repo: NotificationRepository instance
            business_service: NotificationBusinessService instance
            max_retries: Maximum retry attempts per notification
            check_interval: How often to check for retries (seconds)
        """
        self.notification_repo = notification_repo
        self.business_service = business_service
        self.max_retries = max_retries
        self.check_interval = check_interval
        self.running = False
        self.task: Optional[asyncio.Task] = None
        logger.info(
            f"RetryService initialized: max_retries={max_retries}, "
            f"check_interval={check_interval}s"
        )
    
    async def start(self):
        """Start the retry service"""
        if self.running:
            logger.warning("RetryService already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._retry_loop())
        logger.info("RetryService started")
    
    async def stop(self):
        """Stop the retry service"""
        logger.info("Stopping RetryService...")
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("RetryService stopped")
    
    async def _retry_loop(self):
        """Main retry loop - runs periodically"""
        try:
            while self.running:
                try:
                    await self.process_retries()
                except Exception as e:
                    logger.error(f"Error in retry loop: {e}")
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info("Retry loop cancelled")
            raise
    
    async def process_retries(self):
        """Check for and retry failed notifications"""
        try:
            # Get failed notifications eligible for retry
            failed_notifications = await self.notification_repo.get_failed_notifications_for_retry(
                max_retries=self.max_retries
            )
            
            if not failed_notifications:
                logger.debug("No failed notifications to retry")
                return
            
            logger.info(f"Found {len(failed_notifications)} failed notifications to check")
            
            for notification in failed_notifications:
                await self._retry_notification(notification)
                
        except Exception as e:
            logger.error(f"Error processing retries: {e}")
    
    async def _retry_notification(self, notification: dict):
        """
        Retry a single notification if backoff period has elapsed
        
        Args:
            notification: Notification record from database
        """
        notification_id = str(notification['id'])
        retry_count = notification['retry_count']
        created_at = notification['created_at']
        
        # Calculate exponential backoff: 2^retry_count * 60 seconds
        backoff_seconds = (2 ** retry_count) * 60
        
        # Check if enough time has elapsed
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            # Make created_at timezone-aware if it isn't
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        elapsed_seconds = (now - created_at).total_seconds()
        
        if elapsed_seconds < backoff_seconds:
            logger.debug(
                f"Notification {notification_id} not ready for retry: "
                f"elapsed={elapsed_seconds}s, backoff={backoff_seconds}s"
            )
            return
        
        logger.info(
            f"Retrying notification {notification_id}: "
            f"attempt {retry_count + 1}/{self.max_retries}"
        )
        
        try:
            # Increment retry count first
            await self.notification_repo.increment_retry_count(notification_id)
            
            # Retry sending the notification
            result = await self.business_service.send_notification(
                user_id=notification['user_id'],
                notification_type=notification['notification_type'],
                subject=notification['subject'],
                body=notification['body'],
                recipients=notification['recipients'],
                priority=notification['priority']
            )
            
            if result.get("success"):
                logger.info(f"Notification {notification_id} retry successful")
            else:
                logger.warning(
                    f"Notification {notification_id} retry failed: "
                    f"{result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"Error retrying notification {notification_id}: {e}")
    
    def is_running(self) -> bool:
        """Check if retry service is running"""
        return self.running


