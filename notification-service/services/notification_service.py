"""Notification Business Service"""

import asyncio
import logging
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Import metrics (will be set by main.py)
_metrics = None


def set_metrics(metrics):
    """Set metrics module for instrumentation"""
    global _metrics
    _metrics = metrics


class NotificationBusinessService:
    """Business logic for notification operations"""
    
    def __init__(self, notification_repository, email_provider, sms_provider=None):
        self.notification_repo = notification_repository
        self.email_provider = email_provider
        self.sms_provider = sms_provider
        logger.info("NotificationBusinessService initialized")
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        subject: str,
        body: str,
        recipients: List[str],
        priority: str = "normal",
        from_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a notification
        
        Args:
            user_id: User identifier
            notification_type: Type (email, sms, push, sns)
            subject: Notification subject
            body: Notification body
            recipients: List of recipient addresses
            priority: Priority level
            from_address: Optional sender address (for email)
            
        Returns:
            Notification result with notification_id and status
        """
        logger.info(
            f"Sending notification: user={user_id}, type={notification_type}, "
            f"priority={priority}, recipients={len(recipients)}"
        )
        
        # Track timing
        start_time = time.time()
        
        # Validate recipients for email
        if notification_type == "email":
            valid_recipients = [r for r in recipients if self._validate_email(r)]
            if not valid_recipients:
                logger.error("No valid email recipients provided")
                return {
                    "success": False,
                    "error": "No valid email recipients",
                    "notification_id": None
                }
            recipients = valid_recipients
        
        # 1. Create notification record in database
        try:
            notification = await self.notification_repo.create_notification(
                user_id=user_id,
                notification_type=notification_type,
                subject=subject,
                body=body,
                recipients=recipients,
                priority=priority
            )
            notification_id = str(notification['id'])
        except Exception as e:
            logger.error(f"Failed to create notification record: {e}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "notification_id": None
            }
        
        # 2. Route to appropriate provider based on type
        try:
            if notification_type == "email":
                result = await self.email_provider.send_email(
                    from_address=from_address or "noreply@crypto-analytics.com",
                    to_addresses=recipients,
                    subject=subject,
                    body_html=body,
                    body_text=body  # Simple text version
                )
                
                # 3. Update delivery status based on provider response
                if result.get("success"):
                    await self.notification_repo.update_status(
                        notification_id=notification_id,
                        status="sent",
                        sent_at=datetime.utcnow()
                    )
                    
                    # Track metrics
                    if _metrics:
                        _metrics.notifications_sent_total.labels(
                            status='sent', type=notification_type
                        ).inc()
                        _metrics.notification_send_duration_seconds.labels(
                            type=notification_type
                        ).observe(time.time() - start_time)
                    
                    logger.info(f"Notification {notification_id} sent successfully")
                    return {
                        "success": True,
                        "notification_id": notification_id,
                        "message_id": result.get("message_id"),
                        "status": "sent"
                    }
                else:
                    error_message = result.get("error", "Unknown error")
                    await self.notification_repo.update_status(
                        notification_id=notification_id,
                        status="failed",
                        error_message=error_message
                    )
                    
                    # Track metrics
                    if _metrics:
                        _metrics.notifications_sent_total.labels(
                            status='failed', type=notification_type
                        ).inc()
                    
                    logger.error(f"Notification {notification_id} failed: {error_message}")
                    return {
                        "success": False,
                        "notification_id": notification_id,
                        "error": error_message,
                        "status": "failed"
                    }
            
            elif notification_type == "sms":
                # SMS provider not yet implemented
                await self.notification_repo.update_status(
                    notification_id=notification_id,
                    status="failed",
                    error_message="SMS provider not implemented"
                )
                return {
                    "success": False,
                    "notification_id": notification_id,
                    "error": "SMS provider not implemented",
                    "status": "failed"
                }
            
            else:
                await self.notification_repo.update_status(
                    notification_id=notification_id,
                    status="failed",
                    error_message=f"Unsupported notification type: {notification_type}"
                )
                return {
                    "success": False,
                    "notification_id": notification_id,
                    "error": f"Unsupported notification type: {notification_type}",
                    "status": "failed"
                }
                
        except Exception as e:
            logger.error(f"Error sending notification {notification_id}: {e}")
            try:
                await self.notification_repo.update_status(
                    notification_id=notification_id,
                    status="failed",
                    error_message=str(e)
                )
            except Exception as db_error:
                logger.error(f"Failed to update notification status: {db_error}")
            
            return {
                "success": False,
                "notification_id": notification_id,
                "error": str(e),
                "status": "failed"
            }
    
    async def process_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an alert event from Kafka and send notification
        
        Args:
            alert: Alert event data containing user_id, symbol, condition info
            
        Returns:
            Result of notification sending
        """
        logger.info(f"Processing alert: {alert.get('alert_id', 'unknown')}")
        
        try:
            # Extract alert details
            user_id = alert.get("user_id")
            symbol = alert.get("symbol")
            condition_type = alert.get("condition_type")
            threshold_value = alert.get("threshold_value")
            triggered_value = alert.get("triggered_value")
            message = alert.get("message", "Alert triggered")
            
            if not user_id:
                logger.error("Alert missing user_id")
                return {"success": False, "error": "Missing user_id"}
            
            # Get user email from database
            user_email = await self.notification_repo.get_user_email(user_id)
            if not user_email:
                logger.error(f"No email found for user {user_id}")
                return {"success": False, "error": "User email not found"}
            
            # Build email subject and body
            subject = f"?? Crypto Alert: {symbol} {condition_type}"
            body = f"""
            <html>
            <body>
                <h2>Crypto Alert Triggered</h2>
                <p><strong>Symbol:</strong> {symbol}</p>
                <p><strong>Condition:</strong> {condition_type}</p>
                <p><strong>Threshold:</strong> {threshold_value}</p>
                <p><strong>Current Value:</strong> {triggered_value}</p>
                <p><strong>Message:</strong> {message}</p>
                <hr>
                <p><em>This is an automated notification from Crypto Analytics Platform</em></p>
            </body>
            </html>
            """
            
            # Send notification
            result = await self.send_notification(
                user_id=user_id,
                notification_type="email",
                subject=subject,
                body=body,
                recipients=[user_email],
                priority="high"  # Alerts are high priority
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_bulk_notifications(
        self,
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send bulk notifications concurrently
        
        Args:
            notifications: List of notification dicts with required fields
            
        Returns:
            Summary with counts and results
        """
        logger.info(f"Sending bulk notifications: {len(notifications)} total")
        
        # Send all notifications concurrently
        tasks = [
            self.send_notification(
                user_id=notif.get("user_id"),
                notification_type=notif.get("notification_type", "email"),
                subject=notif.get("subject"),
                body=notif.get("body"),
                recipients=notif.get("recipients", []),
                priority=notif.get("priority", "normal")
            )
            for notif in notifications
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        total_sent = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        total_failed = len(results) - total_sent
        failed_ids = [
            r.get("notification_id")
            for r in results
            if isinstance(r, dict) and not r.get("success") and r.get("notification_id")
        ]
        
        logger.info(
            f"Bulk send complete: {total_sent} sent, {total_failed} failed"
        )
        
        return {
            "total_requested": len(notifications),
            "total_sent": total_sent,
            "total_failed": total_failed,
            "failed_ids": failed_ids,
            "results": [r for r in results if isinstance(r, dict)]
        }
    
    async def get_notification_status(
        self,
        notification_id: str
    ) -> Dict[str, Any]:
        """
        Get notification delivery status
        
        Args:
            notification_id: Notification ID
            
        Returns:
            Notification details and status
        """
        try:
            notification = await self.notification_repo.get_notification(notification_id)
            
            if not notification:
                return {
                    "success": False,
                    "error": f"Notification {notification_id} not found"
                }
            
            return {
                "success": True,
                "notification_id": str(notification["id"]),
                "status": notification["status"],
                "notification_type": notification["notification_type"],
                "subject": notification["subject"],
                "priority": notification["priority"],
                "retry_count": notification["retry_count"],
                "created_at": notification["created_at"].isoformat(),
                "sent_at": notification["sent_at"].isoformat() if notification["sent_at"] else None,
                "error_message": notification["error_message"]
            }
        except Exception as e:
            logger.error(f"Error getting notification status: {e}")
            return {"success": False, "error": str(e)}
