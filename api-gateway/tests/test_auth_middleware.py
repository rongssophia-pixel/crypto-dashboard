"""Integration tests for authentication middleware"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from shared.auth.jwt_handler import JWTHandler, UserContext
from api_gateway.middleware.auth_middleware import (
    get_current_user,
    get_current_user_optional,
    require_auth
)


# Create test app
app = FastAPI()


@app.get("/public")
async def public_endpoint():
    """Public endpoint - no authentication required"""
    return {"message": "public"}


@app.get("/protected")
async def protected_endpoint(user: UserContext = Depends(require_auth)):
    """Protected endpoint - authentication required"""
    return {"user_id": user.user_id, "email": user.email}


@app.get("/optional")
async def optional_auth_endpoint(user: UserContext = Depends(get_current_user_optional)):
    """Endpoint with optional authentication"""
    if user:
        return {"authenticated": True, "user_id": user.user_id}
    return {"authenticated": False}


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def jwt_handler():
    """Create JWT handler for testing"""
    return JWTHandler(
        secret_key="test-secret-key-for-testing-only",
        algorithm="HS256",
        access_token_expiration_minutes=60,
        refresh_token_expiration_days=7
    )


class TestAuthMiddleware:
    """Test authentication middleware"""
    
    def test_public_endpoint_no_auth(self, client):
        """Test public endpoint without authentication"""
        response = client.get("/public")
        
        assert response.status_code == 200
        assert response.json()["message"] == "public"
    
    def test_protected_endpoint_no_token(self, client):
        """Test protected endpoint without token"""
        response = client.get("/protected")
        
        assert response.status_code == 403  # No credentials
    
    def test_protected_endpoint_invalid_token(self, client):
        """Test protected endpoint with invalid token"""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()
    
    def test_protected_endpoint_malformed_token(self, client):
        """Test protected endpoint with malformed token"""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer not-a-jwt"}
        )
        
        assert response.status_code == 401
    
    def test_protected_endpoint_valid_token(self, client, jwt_handler):
        """Test protected endpoint with valid access token"""
        # Create valid access token
        token = jwt_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-123"
        assert data["email"] == "test@example.com"
    
    def test_protected_endpoint_refresh_token_rejected(self, client, jwt_handler):
        """Test protected endpoint with refresh token (should be rejected)"""
        # Create refresh token (wrong type)
        token = jwt_handler.create_refresh_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401
        assert "type" in response.json()["detail"].lower()
    
    def test_protected_endpoint_wrong_secret(self, client):
        """Test protected endpoint with token signed by different secret"""
        # Create token with different secret
        different_handler = JWTHandler(
            secret_key="different-secret-key",
            algorithm="HS256"
        )
        token = different_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401
    
    def test_optional_auth_no_token(self, client):
        """Test optional auth endpoint without token"""
        response = client.get("/optional")
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
    
    def test_optional_auth_with_token(self, client, jwt_handler):
        """Test optional auth endpoint with valid token"""
        token = jwt_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.get(
            "/optional",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == "test-user-123"
    
    def test_optional_auth_invalid_token(self, client):
        """Test optional auth endpoint with invalid token"""
        response = client.get(
            "/optional",
            headers={"Authorization": "Bearer invalid.token"}
        )
        
        # Should return 401 even for optional auth if token is invalid
        assert response.status_code == 401
    
    def test_bearer_scheme_case_insensitive(self, client, jwt_handler):
        """Test that Bearer scheme is case insensitive"""
        token = jwt_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        # Try with lowercase 'bearer'
        response = client.get(
            "/protected",
            headers={"Authorization": f"bearer {token}"}
        )
        
        # Should work (HTTP headers are case-insensitive)
        assert response.status_code == 200
    
    def test_missing_bearer_prefix(self, client, jwt_handler):
        """Test token without Bearer prefix"""
        token = jwt_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        # Send token without Bearer prefix
        response = client.get(
            "/protected",
            headers={"Authorization": token}
        )
        
        # Should fail
        assert response.status_code == 403
    
    def test_token_with_additional_claims(self, client, jwt_handler):
        """Test token with additional claims"""
        token = jwt_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com",
            additional_claims={
                "roles": ["admin", "user"],
                "organization": "test-org"
            }
        )
        
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        # Additional claims are available in the UserContext
        # but not returned in this endpoint
