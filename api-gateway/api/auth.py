"""
Authentication API Endpoints
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
import logging

from shared.auth.jwt_handler import JWTHandler, UserContext
from shared.auth.password import PasswordHandler
from repositories.user_repository import UserRepository
from repositories.token_repository import TokenRepository
from services.email_service import EmailService
from middleware.auth_middleware import require_auth
from config import settings
from jose import JWTError

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize handlers and repositories
jwt_handler = JWTHandler(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    access_token_expiration_minutes=settings.access_token_expiration_minutes,
    refresh_token_expiration_days=settings.refresh_token_expiration_days
)

user_repo = UserRepository(
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_db,
    user=settings.postgres_user,
    password=settings.postgres_password
)

token_repo = TokenRepository(
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_db,
    user=settings.postgres_user,
    password=settings.postgres_password
)

email_service = EmailService(
    host=settings.notification_service_host,
    port=settings.notification_service_port
)


# ========================================
# Request/Response Models
# ========================================

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    """Email verification request"""
    token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    token: str
    new_password: str


class LogoutRequest(BaseModel):
    """Logout request"""
    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True


# ========================================
# Authentication Endpoints
# ========================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    User registration endpoint
    
    Creates a new user account and returns access + refresh tokens.
    Sends verification email to user.
    """
    try:
        # Validate password strength
        is_strong, error_msg = PasswordHandler.is_password_strong(request.password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Hash password
        password_hash = PasswordHandler.hash_password(request.password)
        
        # Create user (is_active=True to allow immediate use)
        user = await user_repo.create_user(
            email=request.email,
            password_hash=password_hash,
            roles=["user"],
            is_active=True
        )
        
        # Generate tokens
        access_token = jwt_handler.create_access_token(
            user_id=user["id"],
            email=user["email"]
        )
        
        refresh_token = jwt_handler.create_refresh_token(
            user_id=user["id"],
            email=user["email"]
        )
        
        # Store refresh token
        refresh_payload = jwt_handler.decode_token(refresh_token, verify=False)
        expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        await token_repo.store_refresh_token(
            user_id=user["id"],
            token_jti=refresh_payload["jti"],
            expires_at=expires_at
        )
        
        # Send verification email (non-blocking, don't fail registration if it fails)
        try:
            verification_token = jwt_handler.create_verification_token(
                user_id=user["id"],
                email=user["email"],
                expiration_hours=settings.verification_token_expiration_hours
            )
            
            await email_service.send_verification_email(
                user_id=user["id"],
                email=user["email"],
                verification_token=verification_token,
                frontend_url=settings.frontend_url
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            # Don't fail registration if email fails
        
        logger.info(f"User registered successfully: {user['email']}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expiration_minutes * 60
        )
    
    except HTTPException:
        # Re-raise HTTPExceptions (like password validation errors)
        raise
    except ValueError as e:
        # Email already exists
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    User login endpoint
    
    Validates credentials and returns access + refresh tokens.
    """
    try:
        # Get user by email
        user = await user_repo.get_user_by_email(request.email)
        
        if not user:
            # Don't reveal if user exists
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not PasswordHandler.verify_password(request.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login timestamp
        await user_repo.update_last_login(user["id"])
        
        # Generate tokens
        access_token = jwt_handler.create_access_token(
            user_id=user["id"],
            email=user["email"]
        )
        
        refresh_token = jwt_handler.create_refresh_token(
            user_id=user["id"],
            email=user["email"]
        )
        
        # Store refresh token
        refresh_payload = jwt_handler.decode_token(refresh_token, verify=False)
        expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        await token_repo.store_refresh_token(
            user_id=user["id"],
            token_jti=refresh_payload["jti"],
            expires_at=expires_at
        )
        
        logger.info(f"User logged in successfully: {user['email']}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expiration_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token
    
    Returns new access token and optionally rotates refresh token.
    """
    try:
        # Verify refresh token
        payload = jwt_handler.verify_token(request.refresh_token, expected_type="refresh")
        
        # Check if token is revoked
        token_jti = payload.get("jti")
        if await token_repo.is_token_revoked(token_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )
        
        # Generate new access token
        access_token = jwt_handler.create_access_token(
            user_id=payload["sub"],
            email=payload["email"]
        )
        
        # Optionally rotate refresh token (for better security)
        new_refresh_token = jwt_handler.create_refresh_token(
            user_id=payload["sub"],
            email=payload["email"]
        )
        
        # Revoke old refresh token
        await token_repo.revoke_token(token_jti)
        
        # Store new refresh token
        new_refresh_payload = jwt_handler.decode_token(new_refresh_token, verify=False)
        expires_at = datetime.fromtimestamp(new_refresh_payload["exp"], tz=timezone.utc)
        await token_repo.store_refresh_token(
            user_id=payload["sub"],
            token_jti=new_refresh_payload["jti"],
            expires_at=expires_at
        )
        
        logger.info(f"Token refreshed for user: {payload['email']}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.access_token_expiration_minutes * 60
        )
        
    except JWTError as e:
        logger.warning(f"Invalid refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    except ValueError as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(request: VerifyEmailRequest):
    """
    Verify user's email address
    
    Accepts verification token from email link.
    """
    try:
        # Verify token
        payload = jwt_handler.verify_token(request.token, expected_type="verification")
        
        # Mark email as verified
        user_id = payload["sub"]
        success = await user_repo.mark_email_verified(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        logger.info(f"Email verified for user: {user_id}")
        
        return MessageResponse(
            message="Email verified successfully",
            success=True
        )
        
    except JWTError as e:
        logger.warning(f"Invalid verification token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request password reset
    
    Sends password reset email if user exists.
    Always returns success to prevent email enumeration.
    """
    try:
        # Get user by email
        user = await user_repo.get_user_by_email(request.email)
        
        if user:
            # Generate password reset token
            reset_token = jwt_handler.create_password_reset_token(
                user_id=user["id"],
                email=user["email"],
                expiration_hours=settings.password_reset_token_expiration_hours
            )
            
            # Send password reset email
            try:
                await email_service.send_password_reset_email(
                    user_id=user["id"],
                    email=user["email"],
                    reset_token=reset_token,
                    frontend_url=settings.frontend_url
                )
                logger.info(f"Password reset email sent to: {request.email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e}")
        else:
            # User doesn't exist, but don't reveal that
            logger.info(f"Password reset requested for non-existent email: {request.email}")
        
        # Always return success to prevent email enumeration
        return MessageResponse(
            message="If an account exists with that email, a password reset link has been sent",
            success=True
        )
        
    except Exception as e:
        logger.error(f"Forgot password failed: {e}")
        # Still return success to prevent information leakage
        return MessageResponse(
            message="If an account exists with that email, a password reset link has been sent",
            success=True
        )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using reset token
    
    Updates user's password and revokes all refresh tokens.
    """
    try:
        # Verify reset token
        payload = jwt_handler.verify_token(request.token, expected_type="password_reset")
        
        # Validate new password strength
        is_strong, error_msg = PasswordHandler.is_password_strong(request.new_password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Hash new password
        password_hash = PasswordHandler.hash_password(request.new_password)
        
        # Update password
        user_id = payload["sub"]
        success = await user_repo.update_password(user_id, password_hash)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Revoke all refresh tokens (force re-login)
        await token_repo.revoke_all_user_tokens(user_id)
        
        # Send password changed notification
        try:
            await email_service.send_password_changed_notification(
                user_id=user_id,
                email=payload["email"]
            )
        except Exception as e:
            logger.error(f"Failed to send password changed notification: {e}")
        
        logger.info(f"Password reset successfully for user: {user_id}")
        
        return MessageResponse(
            message="Password reset successfully. Please log in with your new password.",
            success=True
        )
    
    except HTTPException:
        # Re-raise HTTPExceptions (like password validation errors)
        raise
    except JWTError as e:
        logger.warning(f"Invalid reset token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(request: LogoutRequest):
    """
    Logout user by revoking refresh token
    """
    try:
        # Decode token to get JTI (don't verify since it might be expired)
        payload = jwt_handler.decode_token(request.refresh_token, verify=False)
        token_jti = payload.get("jti")
        
        # Revoke the refresh token
        await token_repo.revoke_token(token_jti)
        
        logger.info(f"User logged out: {payload.get('email')}")
        
        return MessageResponse(
            message="Logged out successfully",
            success=True
        )
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        # Don't fail logout - just return success
        return MessageResponse(
            message="Logged out successfully",
            success=True
        )


@router.get("/me")
async def get_current_user_info(current_user: UserContext = Depends(require_auth)):
    """
    Get current user information (protected endpoint example)
    """
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "roles": current_user.roles
    }
