"""
Password hashing and verification utilities
Uses bcrypt for secure password hashing
"""

import re
from typing import Optional

from passlib.context import CryptContext

# Configure bcrypt context with cost factor 12
# Note: bcrypt 4.0+ requires proper encoding handling
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto", 
    bcrypt__rounds=12,
    bcrypt__ident="2b"  # Use 2b format for better compatibility
)


class PasswordHandler:
    """
    Handler for password hashing and verification using bcrypt
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plain text password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
            
        Note:
            Bcrypt has a 72-byte limit. This implementation properly handles
            encoding to ensure compatibility with bcrypt 4.0+.
        """
        # Ensure password is a string (not bytes)
        if isinstance(password, bytes):
            password = password.decode('utf-8', errors='replace')
        
        # Check byte length (bcrypt has a 72-byte limit)
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # Truncate to 72 bytes, ensuring we don't split a multi-byte character
            password_bytes = password_bytes[:72]
            # Try to decode, removing any incomplete character at the end
            try:
                password = password_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # If we split a multi-byte character, trim and try again
                for i in range(1, 5):  # UTF-8 characters are max 4 bytes
                    try:
                        password = password_bytes[:-i].decode('utf-8')
                        break
                    except UnicodeDecodeError:
                        continue
        
        try:
            # Hash with passlib (it handles the bcrypt encoding internally)
            return pwd_context.hash(password)
        except (ValueError, TypeError) as e:
            # If there's an encoding issue, try with explicit UTF-8 normalization
            import unicodedata
            normalized = unicodedata.normalize('NFKC', password)
            return pwd_context.hash(normalized)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a bcrypt hash
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            # Invalid hash format or other error
            return False
    
    @staticmethod
    def is_password_strong(password: str) -> tuple[bool, Optional[str]]:
        """
        Check if password meets strength requirements
        
        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        
        Args:
            password: Password to check
            
        Returns:
            Tuple of (is_strong, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", password):
            return False, "Password must contain at least one special character"
        
        return True, None

