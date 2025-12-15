"""
Analytics Business Service
Core business logic for analytics queries
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from functools import lru_cache

from repositories.clickhouse_repository import ClickHouseRepository

logger = logging.getLogger(__name__)

# Default limits
DEFAULT_QUERY_LIMIT = 1000
MAX_QUERY_LIMIT = 10000
DEFAULT_CANDLE_LIMIT = 500
MAX_CANDLE_LIMIT = 5000

# Supported metric types
SUPPORTED_METRICS = {
    "avg_price",
    "total_volume", 
    "volatility",
    "min_price",
    "max_price",
    "vwap",
    "trade_count",
    "price_range",
    "price_range_pct",
    "price_change_pct",
}

# Supported candle intervals
SUPPORTED_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}


class AnalyticsBusinessService:
    """
    Business logic for analytics operations
    Coordinates query execution and data transformation
    """
    
    def __init__(self, clickhouse_repository: ClickHouseRepository):
        """Initialize business service with ClickHouse repository"""
        self.clickhouse_repo = clickhouse_repository
        self._cache_enabled = True
        logger.info("AnalyticsBusinessService initialized")
    
    def _validate_time_range(
        self, 
        start_time: datetime, 
        end_time: datetime,
        max_days: int = 365
    ) -> None:
        """
        Validate time range parameters
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            max_days: Maximum allowed day range
            
        Raises:
            ValueError: If validation fails
        """
        if start_time >= end_time:
            raise ValueError("start_time must be before end_time")
        
        delta = end_time - start_time
        if delta.days > max_days:
            raise ValueError(f"Time range exceeds maximum of {max_days} days")
    
    def _validate_symbols(self, symbols: List[str]) -> List[str]:
        """
        Validate and normalize symbol list
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            Normalized symbol list
            
        Raises:
            ValueError: If validation fails
        """
        if not symbols:
            raise ValueError("At least one symbol is required")
        
        if len(symbols) > 50:
            raise ValueError("Maximum 50 symbols per query")
        
        # Normalize to uppercase
        return [s.upper().strip() for s in symbols]
    
    def _validate_limit(
        self, 
        limit: int, 
        default: int, 
        max_limit: int
    ) -> int:
        """Validate and constrain limit parameter"""
        if limit <= 0:
            return default
        return min(limit, max_limit)
    
    async def query_market_data(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
        order_by: str = "timestamp_desc"
    ) -> Dict[str, Any]:
        """
        Query raw market data points
        
        Args:
            symbols: List of trading symbols
            start_time: Start timestamp
            end_time: End timestamp
            limit: Maximum records to return
            offset: Pagination offset
            order_by: Sort order (timestamp_asc, timestamp_desc)
            
        Returns:
            Dictionary with data and metadata
        """
        # Validate parameters
        symbols = self._validate_symbols(symbols)
        self._validate_time_range(start_time, end_time)
        limit = self._validate_limit(limit, DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT)
        offset = max(0, offset)
        
        if order_by not in ("timestamp_asc", "timestamp_desc"):
            order_by = "timestamp_desc"
        
        logger.info(
            f"Querying market data: symbols={symbols}, "
            f"range={start_time} to {end_time}, limit={limit}, offset={offset}"
        )
        
        try:
            result = await self.clickhouse_repo.query_market_data(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset,
                order_by=order_by,
            )

            logger.info(f"Market data query returned {len(result['data'])} records")
            return result
            
        except Exception as e:
            logger.error(f"Error in query_market_data: {e}", exc_info=True)
            raise
    
    async def get_candles(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = DEFAULT_CANDLE_LIMIT
    ) -> Dict[str, Any]:
        """
        Get OHLCV candles
        
        Args:
            symbol: Trading symbol
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            start_time: Start timestamp
            end_time: End timestamp
            limit: Maximum candles to return
            
        Returns:
            Dictionary with candles and metadata
        """
        # Validate parameters
        symbol = symbol.upper().strip()
        if not symbol:
            raise ValueError("Symbol is required")
        
        if interval not in SUPPORTED_INTERVALS:
            raise ValueError(
                f"Invalid interval '{interval}'. Supported: {SUPPORTED_INTERVALS}"
            )
        
        self._validate_time_range(start_time, end_time, max_days=365)
        limit = self._validate_limit(limit, DEFAULT_CANDLE_LIMIT, MAX_CANDLE_LIMIT)
        
        logger.info(
            f"Getting candles: symbol={symbol}, "
            f"interval={interval}, range={start_time} to {end_time}, limit={limit}"
        )
        
        try:
            result = await self.clickhouse_repo.query_candles(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
            
            logger.info(f"Candle query returned {len(result['candles'])} candles")
            return result
            
        except Exception as e:
            logger.error(f"Error in get_candles: {e}", exc_info=True)
            raise
    
    async def get_aggregated_metrics(
        self,
        symbol: str,
        metric_types: List[str],
        start_time: datetime,
        end_time: datetime,
        time_bucket: str = "1h"
    ) -> Dict[str, Any]:
        """
        Calculate aggregated metrics
        
        Args:
            symbol: Trading symbol
            metric_types: List of metrics to calculate
            start_time: Start timestamp
            end_time: End timestamp
            time_bucket: Time bucket for time series (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
            
        Returns:
            Dictionary of metric values and time series
        """
        # Validate parameters
        symbol = symbol.upper().strip()
        if not symbol:
            raise ValueError("Symbol is required")
        
        if not metric_types:
            metric_types = ["avg_price", "total_volume"]
        
        # Filter to supported metrics
        valid_metrics = [m for m in metric_types if m in SUPPORTED_METRICS]
        if not valid_metrics:
            raise ValueError(
                f"No valid metrics provided. Supported: {SUPPORTED_METRICS}"
            )
        
        self._validate_time_range(start_time, end_time, max_days=365)
        
        # Validate time bucket
        valid_buckets = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"}
        if time_bucket not in valid_buckets:
            time_bucket = "1h"
        
        logger.info(
            f"Getting aggregated metrics: symbol={symbol}, "
            f"metrics={valid_metrics}, range={start_time} to {end_time}, bucket={time_bucket}"
        )
        
        try:
            result = await self.clickhouse_repo.calculate_aggregates(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                metric_types=valid_metrics,
                time_bucket=time_bucket,
            )
            
            logger.info(
                f"Aggregation query returned {len(result['metrics'])} metrics, "
                f"{len(result['time_series'])} time series points"
            )
            return result
            
        except Exception as e:
            logger.error(f"Error in get_aggregated_metrics: {e}", exc_info=True)
            raise
    
    async def get_latest_price(
        self,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest price for a single symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest price data or None
        """
        symbol = symbol.upper().strip()
        if not symbol:
            raise ValueError("Symbol is required")
        
        logger.debug(f"Getting latest price: symbol={symbol}")
        
        try:
            return await self.clickhouse_repo.get_latest_price(
                symbol=symbol,
            )
        except Exception as e:
            logger.error(f"Error in get_latest_price: {e}", exc_info=True)
            raise
    
    async def get_latest_prices(
        self,
        symbols: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get latest prices for multiple symbols
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            List of latest price data
        """
        symbols = self._validate_symbols(symbols)
        
        logger.debug(f"Getting latest prices: symbols={symbols}")
        
        try:
            return await self.clickhouse_repo.get_latest_prices_batch(
                symbols=symbols,
            )
        except Exception as e:
            logger.error(f"Error in get_latest_prices: {e}", exc_info=True)
            raise
    
    async def get_price_alerts_data(
        self,
        symbol: str,
        threshold: float,
        comparison: str = "above"
    ) -> Dict[str, Any]:
        """
        Get data for price alert evaluation
        
        Args:
            symbol: Trading symbol
            threshold: Price threshold
            comparison: Comparison type (above, below)
            
        Returns:
            Alert evaluation data
        """
        latest = await self.get_latest_price(symbol)
        
        if not latest:
            return {
                "triggered": False,
                "reason": "no_data",
            }
        
        current_price = latest["price"]
        triggered = False
        
        if comparison == "above" and current_price > threshold:
            triggered = True
        elif comparison == "below" and current_price < threshold:
            triggered = True
        
        return {
            "triggered": triggered,
            "current_price": current_price,
            "threshold": threshold,
            "comparison": comparison,
            "timestamp": latest["timestamp"],
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "repository_stats": self.clickhouse_repo.get_stats(),
            "cache_enabled": self._cache_enabled,
            "supported_metrics": list(SUPPORTED_METRICS),
            "supported_intervals": list(SUPPORTED_INTERVALS),
        }
