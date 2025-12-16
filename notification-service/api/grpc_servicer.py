"""Notification Service gRPC Servicer"""

import logging
from datetime import datetime, timezone
from typing import Optional

import grpc
from proto import notification_pb2, notification_pb2_grpc, common_pb2

logger = logging.getLogger(__name__)


class NotificationServiceServicer(notification_pb2_grpc.NotificationServiceServicer):
    """gRPC servicer for Notification Service"""
    
    def __init__(self, business_service, notification_repo):
        self.business_service = business_service
        self.notification_repo = notification_repo
        logger.info("NotificationServiceServicer initialized")
    
    def _map_priority(self, priority_enum: int) -> str:
        """Map proto Priority enum to string"""
        priority_map = {
            0: "low",
            1: "normal",
            2: "high",
            3: "urgent"
        }
        return priority_map.get(priority_enum, "normal")
    
    def _map_notification_type(self, type_enum: int) -> str:
        """Map proto NotificationType enum to string"""
        type_map = {
            0: "email",
            1: "sms",
            2: "push",
            3: "sns",
            4: "webhook"
        }
        return type_map.get(type_enum, "email")
    
    def _create_timestamp(self, dt: Optional[datetime]) -> Optional[common_pb2.Timestamp]:
        """Convert datetime to proto Timestamp"""
        if dt is None:
            return None
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        timestamp = common_pb2.Timestamp()
        timestamp.seconds = int(dt.timestamp())
        timestamp.nanos = dt.microsecond * 1000
        return timestamp
    
    async def SendNotification(self, request, context):
        """Send a single notification"""
        try:
            # Extract request fields
            user_id = request.user_id
            notification_type = self._map_notification_type(request.type)
            subject = request.subject
            body = request.body
            recipients = list(request.recipients)
            priority = self._map_priority(request.priority)
            
            logger.info(
                f"gRPC SendNotification: user={user_id}, type={notification_type}, "
                f"recipients={len(recipients)}"
            )
            
            # Validate required fields
            if not user_id or not recipients:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id and recipients are required")
                return notification_pb2.NotificationResponse()
            
            # Call business service
            result = await self.business_service.send_notification(
                user_id=user_id,
                notification_type=notification_type,
                subject=subject,
                body=body,
                recipients=recipients,
                priority=priority
            )
            
            # Build response
            response = notification_pb2.NotificationResponse()
            response.notification_id = result.get("notification_id", "")
            response.success = result.get("success", False)
            response.message = result.get("error", "") if not result.get("success") else "Notification sent"
            response.sent_at.CopyFrom(self._create_timestamp(datetime.utcnow()))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in SendNotification: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return notification_pb2.NotificationResponse()
    
    async def SendBulkNotifications(self, request, context):
        """Send bulk notifications"""
        try:
            logger.info(f"gRPC SendBulkNotifications: {len(request.notifications)} notifications")
            
            # Convert proto notifications to dict format
            notifications = []
            for notif_request in request.notifications:
                notifications.append({
                    "user_id": notif_request.user_id,
                    "notification_type": self._map_notification_type(notif_request.type),
                    "subject": notif_request.subject,
                    "body": notif_request.body,
                    "recipients": list(notif_request.recipients),
                    "priority": self._map_priority(notif_request.priority)
                })
            
            # Call business service
            result = await self.business_service.send_bulk_notifications(notifications)
            
            # Build response
            response = notification_pb2.BulkNotificationResponse()
            response.total_requested = result.get("total_requested", 0)
            response.total_sent = result.get("total_sent", 0)
            response.total_failed = result.get("total_failed", 0)
            response.failed_ids.extend(result.get("failed_ids", []))
            
            # Add individual results
            for individual_result in result.get("results", []):
                notif_response = notification_pb2.NotificationResponse()
                notif_response.notification_id = individual_result.get("notification_id", "")
                notif_response.success = individual_result.get("success", False)
                notif_response.message = individual_result.get("error", "") if not individual_result.get("success") else "Sent"
                response.results.append(notif_response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in SendBulkNotifications: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return notification_pb2.BulkNotificationResponse()
    
    async def GetNotificationStatus(self, request, context):
        """Get notification delivery status"""
        try:
            notification_id = request.notification_id
            logger.info(f"gRPC GetNotificationStatus: {notification_id}")
            
            if not notification_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("notification_id is required")
                return notification_pb2.NotificationStatusResponse()
            
            # Get notification from repository
            notification = await self.notification_repo.get_notification(notification_id)
            
            if not notification:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Notification {notification_id} not found")
                return notification_pb2.NotificationStatusResponse()
            
            # Build response
            response = notification_pb2.NotificationStatusResponse()
            response.notification_id = str(notification['id'])
            response.status = notification['status']
            response.error_message = notification['error_message'] or ""
            response.retry_count = notification['retry_count']
            
            if notification['created_at']:
                response.created_at.CopyFrom(self._create_timestamp(notification['created_at']))
            if notification['sent_at']:
                response.sent_at.CopyFrom(self._create_timestamp(notification['sent_at']))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in GetNotificationStatus: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return notification_pb2.NotificationStatusResponse()
    
    async def GetNotificationHistory(self, request, context):
        """Get notification history for a user"""
        try:
            user_id = request.user_id
            limit = request.limit or 50
            offset = request.offset or 0
            
            logger.info(f"gRPC GetNotificationHistory: user={user_id}, limit={limit}, offset={offset}")
            
            if not user_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id is required")
                return notification_pb2.NotificationHistoryResponse()
            
            # Convert timestamps
            start_time = datetime.fromtimestamp(request.start_time.seconds, tz=timezone.utc) if request.start_time.seconds else datetime(2000, 1, 1, tzinfo=timezone.utc)
            end_time = datetime.fromtimestamp(request.end_time.seconds, tz=timezone.utc) if request.end_time.seconds else datetime.utcnow().replace(tzinfo=timezone.utc)
            
            # Get history from repository
            history = await self.notification_repo.get_user_history(
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset
            )
            
            # Build response
            response = notification_pb2.NotificationHistoryResponse()
            response.total_count = len(history)
            
            for notif in history:
                record = notification_pb2.NotificationRecord()
                record.notification_id = str(notif['id'])
                record.type = 0  # EMAIL - would need reverse mapping
                record.subject = notif['subject']
                record.status = notif['status']
                
                if notif['created_at']:
                    record.created_at.CopyFrom(self._create_timestamp(notif['created_at']))
                if notif['sent_at']:
                    record.sent_at.CopyFrom(self._create_timestamp(notif['sent_at']))
                
                response.records.append(record)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in GetNotificationHistory: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return notification_pb2.NotificationHistoryResponse()

