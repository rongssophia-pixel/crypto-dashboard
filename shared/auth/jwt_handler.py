"""
JWT Token Handler
Handles creation, validation, and decoding of JWT tokens for authentication
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt


class JWTHandler:
    """
    Handler for JWT token operations using python-jose
    """
    
    def __init__(
        self, 
        secret_key: str, 
        algorithm: str = "HS256", 
        access_token_expiration_minutes: int = 60,
        refresh_token_expiration_days: int = 7
    ):
        """
        Initialize JWT handler
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expiration_minutes: Access token expiration time in minutes
            refresh_token_expiration_days: Refresh token expiration time in days
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expiration_minutes = access_token_expiration_minutes
        self.refresh_token_expiration_days = refresh_token_expiration_days
    
    def create_access_token(
        self, 
        user_id: str,
        email: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new JWT access token
        
        Args:
            user_id: User identifier
            email: User email
            additional_claims: Optional additional claims to include
            
        Returns:
            Encoded JWT token string
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expiration_minutes)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "iat": now,
            "exp": expire,
            "jti": uuid4().hex
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new JWT refresh token
        
        Args:
            user_id: User identifier
            email: User email
            additional_claims: Optional additional claims to include
            
        Returns:
            Encoded JWT token string
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expiration_days)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "iat": now,
            "exp": expire,
            "jti": uuid4().hex
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_verification_token(
        self,
        user_id: str,
        email: str,
        expiration_hours: int = 24
    ) -> str:
        """
        Create a short-lived token for email verification
        
        Args:
            user_id: User identifier
            email: User email
            expiration_hours: Token expiration in hours (default: 24)
            
        Returns:
            Encoded JWT token string
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=expiration_hours)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "verification",
            "iat": now,
            "exp": expire,
            "jti": uuid4().hex
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_password_reset_token(
        self,
        user_id: str,
        email: str,
        expiration_hours: int = 1
    ) -> str:
        """
        Create a short-lived token for password reset
        
        Args:
            user_id: User identifier
            email: User email
            expiration_hours: Token expiration in hours (default: 1)
            
        Returns:
            Encoded JWT token string
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=expiration_hours)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "password_reset",
            "iat": now,
            "exp": expire,
            "jti": uuid4().hex
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token string
            expected_type: Expected token type (access, refresh, verification, password_reset)
            
        Returns:
            Decoded token claims
            
        Raises:
            JWTError: If token is invalid or expired
            ValueError: If token type doesn't match expected type
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type if specified
            if expected_type and payload.get("type") != expected_type:
                raise ValueError(f"Invalid token type. Expected {expected_type}, got {payload.get('type')}")
            
            return payload
        except JWTError as e:
            raise JWTError(f"Token validation failed: {str(e)}")
    
    def decode_token(self, token: str, verify: bool = True) -> Dict[str, Any]:
        """
        Decode a JWT token
        
        Args:
            token: JWT token string
            verify: Whether to verify the signature (default: True)
            
        Returns:
            Decoded token claims
            
        Raises:
            JWTError: If token cannot be decoded
        """
        options = {"verify_signature": verify, "verify_exp": verify}
        return jwt.decode(
            token, 
            self.secret_key, 
            algorithms=[self.algorithm],
            options=options
        )

class UserContext:
    """
    User context extracted from JWT token
    Used for authentication throughout the application
    """
    
    def __init__(self, user_id: str, email: str, roles: Optional[list[str]] = None):
        """
        Initialize user context
        
        Args:
            user_id: User identifier
            email: User email
            roles: User roles (optional)
        """
        self.user_id = user_id
        self.email = email
        self.roles = roles or []
    
    def has_role(self, role: str) -> bool:
        """
        Check if user has a specific role
        
        Args:
            role: Role name to check
            
        Returns:
            True if user has the role, False otherwise
        """
        return role in self.roles
    
    def is_admin(self) -> bool:
        """
        Check if user has admin role
        
        Returns:
            True if user is admin, False otherwise
        """
        return self.has_role("admin")
    
    @classmethod
    def from_token_payload(cls, payload: Dict[str, Any]) -> "UserContext":
        """
        Create UserContext from JWT token payload
        
        Args:
            payload: Decoded JWT token payload
            
        Returns:
            UserContext instance
        """
        return cls(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            roles=payload.get("roles", [])
        )
