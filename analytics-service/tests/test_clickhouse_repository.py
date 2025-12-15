"""
Unit tests for ClickHouse Repository
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.clickhouse_repository import (
    ClickHouseRepository,
    VALID_INTERVALS,
)


class TestClickHouseRepository:
    """Tests for ClickHouseRepository"""
    
    @pytest.fixture
    def repository(self):
        """Create repository instance"""
        return ClickHouseRepository(
            host="localhost",
            port=9000,
            database="test_db",
            user="default",
            password="",
        )
    
    def test_init_sets_connection_params(self, repository):
        """Test that init sets connection parameters"""
        assert repository.host == "localhost"
        assert repository.port == 9000
        assert repository.database == "test_db"
        assert repository.user == "default"
        assert repository.client is None  # Not connected yet
    
    @pytest.mark.asyncio
    async def test_query_market_data_raises_without_connection(self, repository):
        """Test that queries raise error without connection"""
        with pytest.raises(RuntimeError, match="not connected"):
            await repository.query_market_data(
                symbols=["BTCUSDT"],
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
                limit=100,
                offset=0,
            )
    
    @pytest.mark.asyncio
    async def test_query_candles_raises_without_connection(self, repository):
        """Test that candle query raises error without connection"""
        with pytest.raises(RuntimeError, match="not connected"):
            await repository.query_candles(
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
                limit=100,
            )
    
    @pytest.mark.asyncio
    async def test_query_candles_validates_interval(self, repository):
        """Test that invalid interval raises ValueError"""
        repository.client = MagicMock()  # Fake connection
        
        with pytest.raises(ValueError, match="Invalid interval"):
            await repository.query_candles(
                symbol="BTCUSDT",
                interval="2h",  # Invalid
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
                limit=100,
            )
    
    @pytest.mark.asyncio
    async def test_query_market_data_with_mock_client(self, repository):
        """Test query_market_data with mocked client"""
        mock_client = MagicMock()
        now = datetime.utcnow()
        
        # Mock return values
        mock_client.execute.side_effect = [
            # Data query result
            [
                ("BTCUSDT", now, 50000.0, 100.0, 49990.0, 50010.0, 51000.0, 49000.0, 10000.0, 500.0, 1.01, 1000),
            ],
            # Count query result
            [(1,)],
        ]
        repository.client = mock_client
        
        result = await repository.query_market_data(
            symbols=["BTCUSDT"],
            start_time=now - timedelta(hours=1),
            end_time=now,
            limit=100,
            offset=0,
        )
        
        assert result["total_count"] == 1
        assert len(result["data"]) == 1
        assert result["data"][0]["symbol"] == "BTCUSDT"
        assert result["data"][0]["price"] == 50000.0
    
    @pytest.mark.asyncio
    async def test_query_candles_with_mock_client(self, repository):
        """Test query_candles with mocked client"""
        mock_client = MagicMock()
        now = datetime.utcnow()
        
        mock_client.execute.return_value = [
            (now, 50000.0, 50500.0, 49500.0, 50200.0, 1000.0, 500),
        ]
        repository.client = mock_client
        
        result = await repository.query_candles(
            symbol="BTCUSDT",
            interval="1h",
            start_time=now - timedelta(hours=1),
            end_time=now,
            limit=100,
        )
        
        assert len(result["candles"]) == 1
        candle = result["candles"][0]
        assert candle["open"] == 50000.0
        assert candle["high"] == 50500.0
        assert candle["low"] == 49500.0
        assert candle["close"] == 50200.0
    
    def test_get_stats_disconnected(self, repository):
        """Test get_stats when disconnected"""
        stats = repository.get_stats()
        assert stats["connected"] is False
        assert stats["host"] == "localhost"
        assert stats["port"] == 9000
    
    def test_get_stats_connected(self, repository):
        """Test get_stats when connected"""
        repository.client = MagicMock()
        stats = repository.get_stats()
        assert stats["connected"] is True


class TestValidIntervals:
    """Tests for interval validation"""
    
    def test_valid_intervals_contains_standard(self):
        """Test that standard intervals are valid"""
        standard = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        for interval in standard:
            assert interval in VALID_INTERVALS
