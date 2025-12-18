"""
Authentication Middleware
Validates JWT tokens and extracts user context
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from shared.auth.jwt_handler import JWTHandler, UserContext
from config import settings

logger = logging.getLogger(__name__)

# Initialize JWT handler
jwt_handler = JWTHandler(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    access_token_expiration_minutes=settings.access_token_expiration_minutes,
    refresh_token_expiration_days=settings.refresh_token_expiration_days
)

# Security schemes
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserContext:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        UserContext with user information
        
    Raises:
        HTTPException: If token is invalid, expired, or missing
    """
    token = credentials.credentials
    
    try:
        # Verify token and get payload
        payload = jwt_handler.verify_token(token, expected_type="access")
        
        # Create user context from payload
        user_context = UserContext.from_token_payload(payload)
        
        return user_context
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        logger.warning(f"Invalid token type: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security)
) -> Optional[UserContext]:
    """
    Optional authentication dependency
    Returns None if no token provided, validates token if present
    
    Args:
        credentials: Optional HTTP Bearer token credentials
        
    Returns:
        UserContext if token is valid, None if no token provided
        
    Raises:
        HTTPException: If token is provided but invalid
    """
    if credentials is None:
        return None
    
    # If credentials provided, validate them
    return await get_current_user(credentials)


# Convenience alias for protected endpoints
require_auth = get_current_user
