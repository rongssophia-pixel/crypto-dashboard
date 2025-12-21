"""Unit tests for JWTHandler"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from jose import JWTError
from .jwt_handler import JWTHandler, UserContext


@pytest.fixture
def jwt_handler():
    """Create JWTHandler instance for testing"""
    return JWTHandler(
        secret_key="test-secret-key-for-testing-only",
        algorithm="HS256",
        access_token_expiration_minutes=60,
        refresh_token_expiration_days=7
    )


class TestJWTHandler:
    """Test JWT token operations"""
    
    def test_create_access_token(self, jwt_handler):
        """Test access token creation"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_access_token(user_id, email)
        
        # Token should not be empty
        assert token
        # Token should have 3 parts (header.payload.signature)
        assert len(token.split(".")) == 3
    
    def test_create_refresh_token(self, jwt_handler):
        """Test refresh token creation"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_refresh_token(user_id, email)
        
        # Token should not be empty
        assert token
        # Token should have 3 parts
        assert len(token.split(".")) == 3
    
    def test_verify_access_token(self, jwt_handler):
        """Test access token verification"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_access_token(user_id, email)
        payload = jwt_handler.verify_token(token, expected_type="access")
        
        # Verify payload contents
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload
    
    def test_verify_refresh_token(self, jwt_handler):
        """Test refresh token verification"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_refresh_token(user_id, email)
        payload = jwt_handler.verify_token(token, expected_type="refresh")
        
        # Verify payload contents
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "refresh"
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload
    
    def test_verify_token_wrong_type(self, jwt_handler):
        """Test token verification with wrong expected type"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        # Create access token but expect refresh token
        token = jwt_handler.create_access_token(user_id, email)
        
        with pytest.raises(ValueError, match="Invalid token type"):
            jwt_handler.verify_token(token, expected_type="refresh")
    
    def test_verify_token_invalid_signature(self, jwt_handler):
        """Test token verification with invalid signature"""
        # Create token with one handler
        token = jwt_handler.create_access_token("test-user", "test@example.com")
        
        # Try to verify with different secret key
        different_handler = JWTHandler(
            secret_key="different-secret-key",
            algorithm="HS256"
        )
        
        with pytest.raises(JWTError):
            different_handler.verify_token(token)
    
    def test_verify_token_malformed(self, jwt_handler):
        """Test token verification with malformed token"""
        malformed_token = "not.a.valid.token"
        
        with pytest.raises(JWTError):
            jwt_handler.verify_token(malformed_token)
    
    def test_create_verification_token(self, jwt_handler):
        """Test verification token creation"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_verification_token(user_id, email, expiration_hours=24)
        payload = jwt_handler.verify_token(token, expected_type="verification")
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "verification"
    
    def test_create_password_reset_token(self, jwt_handler):
        """Test password reset token creation"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_password_reset_token(user_id, email, expiration_hours=1)
        payload = jwt_handler.verify_token(token, expected_type="password_reset")
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "password_reset"
    
    def test_decode_token_with_verification(self, jwt_handler):
        """Test token decoding with verification"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_access_token(user_id, email)
        payload = jwt_handler.decode_token(token, verify=True)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
    
    def test_decode_token_without_verification(self, jwt_handler):
        """Test token decoding without verification"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_access_token(user_id, email)
        payload = jwt_handler.decode_token(token, verify=False)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
    
    def test_token_expiration_time(self, jwt_handler):
        """Test that token has correct expiration time"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        before = datetime.now(timezone.utc)
        token = jwt_handler.create_access_token(user_id, email)
        after = datetime.now(timezone.utc)
        
        payload = jwt_handler.decode_token(token, verify=False)
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # Token should expire in approximately 60 minutes (allow 1 minute margin)
        expected_expiry = before + timedelta(minutes=60)
        assert abs((exp_datetime - expected_expiry).total_seconds()) < 60
    
    def test_token_unique_jti(self, jwt_handler):
        """Test that each token has unique JTI"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token1 = jwt_handler.create_access_token(user_id, email)
        token2 = jwt_handler.create_access_token(user_id, email)
        
        payload1 = jwt_handler.decode_token(token1, verify=False)
        payload2 = jwt_handler.decode_token(token2, verify=False)
        
        # JTIs should be different
        assert payload1["jti"] != payload2["jti"]
    
    def test_token_with_additional_claims(self, jwt_handler):
        """Test token creation with additional claims"""
        user_id = "test-user-123"
        email = "test@example.com"
        additional_claims = {
            "role": "admin",
            "organization": "test-org"
        }
        
        token = jwt_handler.create_access_token(
            user_id, 
            email, 
            additional_claims=additional_claims
        )
        payload = jwt_handler.verify_token(token)
        
        # Additional claims should be present
        assert payload["role"] == "admin"
        assert payload["organization"] == "test-org"


class TestUserContext:
    """Test UserContext class"""
    
    def test_user_context_creation(self):
        """Test UserContext creation"""
        user_id = "test-user-123"
        email = "test@example.com"
        roles = ["user", "admin"]
        
        context = UserContext(user_id, email, roles)
        
        assert context.user_id == user_id
        assert context.email == email
        assert context.roles == roles
    
    def test_user_context_default_roles(self):
        """Test UserContext with default empty roles"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        context = UserContext(user_id, email)
        
        assert context.roles == []
    
    def test_has_role(self):
        """Test has_role method"""
        context = UserContext("user-123", "test@example.com", ["user", "admin"])
        
        assert context.has_role("user") is True
        assert context.has_role("admin") is True
        assert context.has_role("superadmin") is False
    
    def test_is_admin(self):
        """Test is_admin method"""
        admin_context = UserContext("user-1", "admin@example.com", ["admin", "user"])
        user_context = UserContext("user-2", "user@example.com", ["user"])
        
        assert admin_context.is_admin() is True
        assert user_context.is_admin() is False
    
    def test_from_token_payload(self, jwt_handler):
        """Test UserContext creation from token payload"""
        user_id = "test-user-123"
        email = "test@example.com"
        roles = ["user", "admin"]
        
        token = jwt_handler.create_access_token(
            user_id, 
            email,
            additional_claims={"roles": roles}
        )
        payload = jwt_handler.verify_token(token)
        
        context = UserContext.from_token_payload(payload)
        
        assert context.user_id == user_id
        assert context.email == email
        assert context.roles == roles
    
    def test_from_token_payload_no_roles(self, jwt_handler):
        """Test UserContext creation from payload without roles"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = jwt_handler.create_access_token(user_id, email)
        payload = jwt_handler.verify_token(token)
        
        context = UserContext.from_token_payload(payload)
        
        assert context.user_id == user_id
        assert context.email == email
        assert context.roles == []
