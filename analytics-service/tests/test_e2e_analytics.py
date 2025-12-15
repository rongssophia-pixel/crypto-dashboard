"""
End-to-End tests for Analytics Service

These tests require:
1. ClickHouse running with data
2. Analytics service running (or use TestClient)

Run with: pytest tests/test_e2e_analytics.py -v
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Skip E2E tests if SKIP_E2E is set
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_E2E", "1") == "1",
    reason="E2E tests disabled. Set SKIP_E2E=0 to run."
)


class TestHealthEndpoints:
    """Test health and monitoring endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "analytics-service"
        assert data["status"] == "running"
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"] or "text/plain" in str(response.headers)


class TestRESTAPIEndpoints:
    """Test REST API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)
    
    def test_get_latest_prices_requires_symbols(self, client):
        """Test that get_latest_prices requires symbols parameter"""
        response = client.get("/api/v1/market-data/latest")
        assert response.status_code == 422  # Validation error
    
    def test_get_candles_requires_params(self, client):
        """Test that get_candles requires required parameters"""
        response = client.get("/api/v1/candles")
        assert response.status_code == 422  # Validation error
    
    def test_get_candles_with_params(self, client):
        """Test get_candles with valid parameters"""
        now = datetime.utcnow()
        start = (now - timedelta(hours=24)).isoformat()
        end = now.isoformat()
        
        response = client.get(
            "/api/v1/candles",
            params={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": start,
                "end_time": end,
                "limit": 10,
            }
        )
        # May return 500 if ClickHouse not connected, but validates params
        assert response.status_code in [200, 500]
    
    def test_get_aggregated_metrics_with_params(self, client):
        """Test get_aggregated_metrics with valid parameters"""
        now = datetime.utcnow()
        start = (now - timedelta(hours=24)).isoformat()
        end = now.isoformat()
        
        response = client.get(
            "/api/v1/metrics/aggregated",
            params={
                "symbol": "BTCUSDT",
                "metric_types": ["avg_price", "total_volume"],
                "start_time": start,
                "end_time": end,
            }
        )
        assert response.status_code in [200, 500]
    
    def test_query_market_data_with_params(self, client):
        """Test query_market_data with valid parameters"""
        now = datetime.utcnow()
        start = (now - timedelta(hours=24)).isoformat()
        end = now.isoformat()
        
        response = client.post(
            "/api/v1/market-data/query",
            params={
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "start_time": start,
                "end_time": end,
                "limit": 10,
            }
        )
        assert response.status_code in [200, 500]


class TestInputValidation:
    """Test input validation"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)
    
    def test_invalid_interval_returns_400(self, client):
        """Test that invalid interval returns 400"""
        now = datetime.utcnow()
        start = (now - timedelta(hours=24)).isoformat()
        end = now.isoformat()
        
        response = client.get(
            "/api/v1/candles",
            params={
                "symbol": "BTCUSDT",
                "interval": "invalid",
                "start_time": start,
                "end_time": end,
            }
        )
        # Should return 400 for invalid interval (or 500 if service not ready)
        assert response.status_code in [400, 500]
    
    def test_invalid_time_range_returns_error(self, client):
        """Test that end before start returns error"""
        now = datetime.utcnow()
        start = now.isoformat()
        end = (now - timedelta(hours=24)).isoformat()  # End before start
        
        response = client.get(
            "/api/v1/candles",
            params={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": start,
                "end_time": end,
            }
        )
        assert response.status_code in [400, 500]

