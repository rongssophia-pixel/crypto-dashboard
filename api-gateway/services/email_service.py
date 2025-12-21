"""Email Service - gRPC client for sending emails via notification service"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for proto imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import grpc
from proto import notification_pb2, notification_pb2_grpc, common_pb2

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service client for sending emails via notification service
    Uses gRPC to communicate with notification service
    """
    
    def __init__(self, host: str, port: int):
        """
        Initialize email service client
        
        Args:
            host: Notification service host
            port: Notification service gRPC port
        """
        self.host = host
        self.port = port
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[notification_pb2_grpc.NotificationServiceStub] = None
        logger.info(f"EmailService initialized for {host}:{port}")
    
    async def connect(self):
        """Establish gRPC connection to notification service"""
        if not self.channel:
            self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
            self.stub = notification_pb2_grpc.NotificationServiceStub(self.channel)
            logger.info("Connected to notification service")
    
    async def disconnect(self):
        """Close gRPC connection"""
        if self.channel:
            await self.channel.close()
            self.channel = None
            self.stub = None
            logger.info("Disconnected from notification service")
    
    async def send_verification_email(
        self,
        user_id: str,
        email: str,
        verification_token: str,
        frontend_url: str
    ) -> bool:
        """
        Send email verification email
        
        Args:
            user_id: User ID
            email: User email address
            verification_token: JWT verification token
            frontend_url: Frontend base URL for verification link
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.stub:
            await self.connect()
        
        verification_link = f"{frontend_url}/verify-email?token={verification_token}"
        
        subject = "Verify your email address"
        body = f"""
        <html>
        <body>
            <h2>Welcome to Crypto Analytics Platform!</h2>
            <p>Thank you for registering. Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Verify Email</a></p>
            <p>Or copy and paste this link into your browser:</p>
            <p>{verification_link}</p>
            <p>This link will expire in 24 hours.</p>
            <p>If you did not create an account, please ignore this email.</p>
        </body>
        </html>
        """
        
        try:
            # Create dummy user context (system request)
            context = common_pb2.UserContext(
                user_id="system",
                tenant_id="system"
            )
            
            request = notification_pb2.NotificationRequest(
                context=context,
                user_id=user_id,
                type=notification_pb2.EMAIL,
                subject=subject,
                body=body,
                recipients=[email],
                priority=notification_pb2.NORMAL
            )
            
            response = await self.stub.SendNotification(request)
            
            if response.success:
                logger.info(f"Verification email sent to {email} (notification_id: {response.notification_id})")
                return True
            else:
                logger.error(f"Failed to send verification email: {response.message}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return False
    
    async def send_password_reset_email(
        self,
        user_id: str,
        email: str,
        reset_token: str,
        frontend_url: str
    ) -> bool:
        """
        Send password reset email
        
        Args:
            user_id: User ID
            email: User email address
            reset_token: JWT password reset token
            frontend_url: Frontend base URL for reset link
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.stub:
            await self.connect()
        
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        subject = "Reset your password"
        body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>We received a request to reset your password for your Crypto Analytics Platform account.</p>
            <p>Click the button below to reset your password:</p>
            <p><a href="{reset_link}" style="background-color: #2196F3; color: white; padding: 14px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Reset Password</a></p>
            <p>Or copy and paste this link into your browser:</p>
            <p>{reset_link}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you did not request a password reset, please ignore this email. Your password will remain unchanged.</p>
        </body>
        </html>
        """
        
        try:
            context = common_pb2.UserContext(
                user_id="system",
                tenant_id="system"
            )
            
            request = notification_pb2.NotificationRequest(
                context=context,
                user_id=user_id,
                type=notification_pb2.EMAIL,
                subject=subject,
                body=body,
                recipients=[email],
                priority=notification_pb2.HIGH
            )
            
            response = await self.stub.SendNotification(request)
            
            if response.success:
                logger.info(f"Password reset email sent to {email} (notification_id: {response.notification_id})")
                return True
            else:
                logger.error(f"Failed to send password reset email: {response.message}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return False
    
    async def send_password_changed_notification(
        self,
        user_id: str,
        email: str
    ) -> bool:
        """
        Send password changed confirmation email
        
        Args:
            user_id: User ID
            email: User email address
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.stub:
            await self.connect()
        
        subject = "Your password has been changed"
        body = """
        <html>
        <body>
            <h2>Password Changed Successfully</h2>
            <p>This email confirms that your password for Crypto Analytics Platform has been changed.</p>
            <p>If you made this change, no further action is required.</p>
            <p>If you did not change your password, please contact support immediately and secure your account.</p>
        </body>
        </html>
        """
        
        try:
            context = common_pb2.UserContext(
                user_id="system",
                tenant_id="system"
            )
            
            request = notification_pb2.NotificationRequest(
                context=context,
                user_id=user_id,
                type=notification_pb2.EMAIL,
                subject=subject,
                body=body,
                recipients=[email],
                priority=notification_pb2.NORMAL
            )
            
            response = await self.stub.SendNotification(request)
            
            if response.success:
                logger.info(f"Password changed notification sent to {email}")
                return True
            else:
                logger.error(f"Failed to send password changed notification: {response.message}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending password changed notification: {e}")
            return False
