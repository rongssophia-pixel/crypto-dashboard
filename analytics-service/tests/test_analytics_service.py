"""
Unit tests for Analytics Business Service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analytics_service import (
    AnalyticsBusinessService,
    SUPPORTED_METRICS,
    SUPPORTED_INTERVALS,
)


class TestAnalyticsBusinessService:
    """Tests for AnalyticsBusinessService"""
    
    def test_validate_symbols_normalizes_to_uppercase(self, analytics_service):
        """Test that symbols are normalized to uppercase"""
        symbols = analytics_service._validate_symbols(["btcusdt", "ethusdt"])
        assert symbols == ["BTCUSDT", "ETHUSDT"]
    
    def test_validate_symbols_strips_whitespace(self, analytics_service):
        """Test that whitespace is stripped from symbols"""
        symbols = analytics_service._validate_symbols(["  BTCUSDT  ", "ETHUSDT "])
        assert symbols == ["BTCUSDT", "ETHUSDT"]
    
    def test_validate_symbols_raises_on_empty(self, analytics_service):
        """Test that empty symbol list raises ValueError"""
        with pytest.raises(ValueError, match="At least one symbol"):
            analytics_service._validate_symbols([])
    
    def test_validate_symbols_raises_on_too_many(self, analytics_service):
        """Test that too many symbols raises ValueError"""
        symbols = [f"SYM{i}" for i in range(51)]
        with pytest.raises(ValueError, match="Maximum 50 symbols"):
            analytics_service._validate_symbols(symbols)
    
    def test_validate_time_range_valid(self, analytics_service):
        """Test that valid time range passes validation"""
        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()
        analytics_service._validate_time_range(start, end)  # Should not raise
    
    def test_validate_time_range_invalid_order(self, analytics_service):
        """Test that start after end raises ValueError"""
        start = datetime.utcnow()
        end = datetime.utcnow() - timedelta(days=1)
        with pytest.raises(ValueError, match="start_time must be before end_time"):
            analytics_service._validate_time_range(start, end)
    
    def test_validate_time_range_too_long(self, analytics_service):
        """Test that too long time range raises ValueError"""
        start = datetime.utcnow() - timedelta(days=400)
        end = datetime.utcnow()
        with pytest.raises(ValueError, match="exceeds maximum"):
            analytics_service._validate_time_range(start, end)
    
    def test_validate_limit_returns_default_for_zero(self, analytics_service):
        """Test that zero limit returns default"""
        result = analytics_service._validate_limit(0, 100, 1000)
        assert result == 100
    
    def test_validate_limit_caps_at_max(self, analytics_service):
        """Test that limit is capped at max"""
        result = analytics_service._validate_limit(5000, 100, 1000)
        assert result == 1000
    
    def test_validate_limit_returns_value_in_range(self, analytics_service):
        """Test that valid limit is returned as-is"""
        result = analytics_service._validate_limit(500, 100, 1000)
        assert result == 500
    
    @pytest.mark.asyncio
    async def test_query_market_data_validates_symbols(self, analytics_service, mock_clickhouse_repository):
        """Test that query_market_data validates symbols"""
        mock_clickhouse_repository.query_market_data = AsyncMock(return_value={
            "data": [],
            "total_count": 0,
            "has_more": False,
        })
        
        result = await analytics_service.query_market_data(
            symbols=["btcusdt"],
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            limit=100,
        )
        
        # Verify normalized symbol was passed to repository
        call_args = mock_clickhouse_repository.query_market_data.call_args
        assert call_args.kwargs["symbols"] == ["BTCUSDT"]
    
    @pytest.mark.asyncio
    async def test_get_candles_validates_interval(self, analytics_service):
        """Test that get_candles validates interval"""
        with pytest.raises(ValueError, match="Invalid interval"):
            await analytics_service.get_candles(
                symbol="BTCUSDT",
                interval="2h",  # Invalid interval
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
            )
    
    @pytest.mark.asyncio
    async def test_get_candles_valid_intervals(self, analytics_service, mock_clickhouse_repository):
        """Test that all supported intervals are accepted"""
        mock_clickhouse_repository.query_candles = AsyncMock(return_value={
            "candles": [],
            "total_count": 0,
        })
        
        for interval in SUPPORTED_INTERVALS:
            result = await analytics_service.get_candles(
                symbol="BTCUSDT",
                interval=interval,
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
            )
            assert "candles" in result
    
    @pytest.mark.asyncio
    async def test_get_aggregated_metrics_filters_invalid_metrics(self, analytics_service, mock_clickhouse_repository):
        """Test that invalid metrics are filtered out"""
        mock_clickhouse_repository.calculate_aggregates = AsyncMock(return_value={
            "symbol": "BTCUSDT",
            "metrics": {"avg_price": 50000},
            "time_series": [],
        })
        
        result = await analytics_service.get_aggregated_metrics(
            symbol="BTCUSDT",
            metric_types=["avg_price", "invalid_metric", "total_volume"],
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
        )
        
        # Verify only valid metrics were passed
        call_args = mock_clickhouse_repository.calculate_aggregates.call_args
        assert "invalid_metric" not in call_args.kwargs["metric_types"]
        assert "avg_price" in call_args.kwargs["metric_types"]
        assert "total_volume" in call_args.kwargs["metric_types"]
    
    def test_get_stats(self, analytics_service):
        """Test get_stats returns expected structure"""
        stats = analytics_service.get_stats()
        
        assert "repository_stats" in stats
        assert "cache_enabled" in stats
        assert "supported_metrics" in stats
        assert "supported_intervals" in stats
        assert set(stats["supported_metrics"]) == SUPPORTED_METRICS
        assert set(stats["supported_intervals"]) == SUPPORTED_INTERVALS


class TestSupportedValues:
    """Tests for module-level constants"""
    
    def test_supported_metrics_contains_expected(self):
        """Test that expected metrics are supported"""
        expected = {"avg_price", "total_volume", "volatility", "vwap"}
        assert expected.issubset(SUPPORTED_METRICS)
    
    def test_supported_intervals_contains_expected(self):
        """Test that expected intervals are supported"""
        expected = {"1m", "5m", "15m", "1h", "4h", "1d"}
        assert expected.issubset(SUPPORTED_INTERVALS)
