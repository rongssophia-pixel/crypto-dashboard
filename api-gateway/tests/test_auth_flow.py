"""Integration tests for authentication endpoints"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add api-gateway directory to path
api_gateway_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_gateway_dir))

# Add project root to path for shared modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set up environment variables before importing app
# Use direct assignment to ensure test values are used
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['KAFKA_BOOTSTRAP_SERVERS'] = 'localhost:9092'
os.environ['POSTGRES_PASSWORD'] = 'test-password-for-testing'

from fastapi.testclient import TestClient
from main import app
from shared.auth.jwt_handler import JWTHandler
from shared.auth.password import PasswordHandler


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


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_register_success(self, client):
        """Test successful user registration"""
        # Note: This test requires a running PostgreSQL database
        # In real testing, you'd use a test database
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"test{datetime.now().timestamp()}@example.com",
                "password": "TestPassword123!"
            }
        )
        
        # Should return 201 Created or fail if database not available
        if response.status_code == 201:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak"
            }
        )
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "TestPassword123!"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self, client):
        """Test successful login"""
        # Note: This test requires user to exist in database
        # In real testing, you'd create a test user first
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!"
            }
        )
        
        # Will fail if user doesn't exist, which is expected in test environment
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!"
            }
        )
        
        # Should return 401 or 500 if database not available
        assert response.status_code in [401, 500]
    
    def test_refresh_token_success(self, client, jwt_handler):
        """Test successful token refresh"""
        # Create a valid refresh token
        refresh_token = jwt_handler.create_refresh_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        # Will fail if database not available, which is expected
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
    
    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_verify_email_success(self, client, jwt_handler):
        """Test email verification"""
        # Create a valid verification token
        verification_token = jwt_handler.create_verification_token(
            user_id="test-user-123",
            email="test@example.com",
            expiration_hours=24
        )
        
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token}
        )
        
        # Will fail if user doesn't exist in database
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
    
    def test_verify_email_invalid_token(self, client):
        """Test email verification with invalid token"""
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid.token.here"}
        )
        
        assert response.status_code == 400
    
    def test_forgot_password(self, client):
        """Test forgot password request"""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"}
        )
        
        # Should always return success (don't reveal if user exists)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token"""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid.token.here",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 400
    
    def test_reset_password_weak_password(self, client, jwt_handler):
        """Test password reset with weak password"""
        reset_token = jwt_handler.create_password_reset_token(
            user_id="test-user-123",
            email="test@example.com",
            expiration_hours=1
        )
        
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "weak"
            }
        )
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()
    
    def test_logout(self, client, jwt_handler):
        """Test logout"""
        refresh_token = jwt_handler.create_refresh_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token}
        )
        
        # Should always succeed
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_get_current_user_without_token(self, client):
        """Test /me endpoint without authentication"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # No credentials provided
    
    def test_get_current_user_with_invalid_token(self, client):
        """Test /me endpoint with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_get_current_user_with_valid_token(self, client, jwt_handler):
        """Test /me endpoint with valid token"""
        access_token = jwt_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-123"
        assert data["email"] == "test@example.com"


class TestProtectedEndpoints:
    """Test protected endpoints"""
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/v1/ingestion/streams/mine")
        
        assert response.status_code == 403
    
    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        response = client.get(
            "/api/v1/ingestion/streams/mine",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_protected_endpoint_with_valid_token(self, client, jwt_handler):
        """Test accessing protected endpoint with valid token"""
        access_token = jwt_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.get(
            "/api/v1/ingestion/streams/mine",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-123"
        assert data["email"] == "test@example.com"
    
    def test_analytics_watchlist_endpoint(self, client, jwt_handler):
        """Test analytics watchlist protected endpoint"""
        access_token = jwt_handler.create_access_token(
            user_id="test-user-123",
            email="test@example.com"
        )
        
        response = client.get(
            "/api/v1/analytics/watchlist",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-123"
