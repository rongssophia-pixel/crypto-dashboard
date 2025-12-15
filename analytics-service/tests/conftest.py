"""
Pytest configuration and fixtures for Analytics Service tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client for unit tests"""
    client = MagicMock()
    client.execute = MagicMock(return_value=[])
    return client


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    now = datetime.utcnow()
    return [
        {
            "symbol": "BTCUSDT",
            "timestamp": now,
            "price": 50000.0,
            "volume": 100.5,
            "bid_price": 49990.0,
            "ask_price": 50010.0,
            "metrics": {
                "high_24h": 51000.0,
                "low_24h": 49000.0,
                "volume_24h": 10000.0,
                "price_change_24h": 500.0,
                "price_change_pct_24h": 1.01,
            },
            "trade_count": 1000,
        },
        {
            "symbol": "ETHUSDT",
            "timestamp": now,
            "price": 3000.0,
            "volume": 500.0,
            "bid_price": 2999.0,
            "ask_price": 3001.0,
            "metrics": {
                "high_24h": 3100.0,
                "low_24h": 2900.0,
                "volume_24h": 50000.0,
                "price_change_24h": 50.0,
                "price_change_pct_24h": 1.69,
            },
            "trade_count": 5000,
        },
    ]


@pytest.fixture
def sample_candles():
    """Sample candle data for testing"""
    now = datetime.utcnow()
    candles = []
    for i in range(10):
        candles.append({
            "timestamp": now - timedelta(hours=i),
            "open": 50000 + i * 100,
            "high": 50500 + i * 100,
            "low": 49500 + i * 100,
            "close": 50200 + i * 100,
            "volume": 1000 + i * 10,
            "trade_count": 500 + i * 5,
        })
    return candles


@pytest.fixture
def mock_clickhouse_repository():
    """Mock ClickHouse repository for service tests"""
    from repositories.clickhouse_repository import ClickHouseRepository
    
    repo = MagicMock(spec=ClickHouseRepository)
    repo.get_stats.return_value = {"connected": True, "host": "localhost", "port": 9000, "database": "test"}
    return repo


@pytest.fixture
def analytics_service(mock_clickhouse_repository):
    """Create analytics service with mocked repository"""
    from services.analytics_service import AnalyticsBusinessService
    return AnalyticsBusinessService(clickhouse_repository=mock_clickhouse_repository)

