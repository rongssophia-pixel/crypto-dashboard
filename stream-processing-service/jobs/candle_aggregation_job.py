"""
Candle Aggregation Job
Aggregates tick data into OHLCV candles
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# Interval duration in seconds
INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


class CandleBuffer:
    """Buffer for accumulating ticks into a candle"""
    
    def __init__(self):
        self.open_price: Optional[float] = None
        self.high_price: float = 0
        self.low_price: float = float("inf")
        self.close_price: float = 0
        self.volume: float = 0
        self.trade_count: int = 0
        self.first_timestamp: Optional[int] = None
        
    def add_tick(self, price: float, volume: float, timestamp: int):
        """Add a tick to the buffer"""
        if self.open_price is None:
            self.open_price = price
            self.first_timestamp = timestamp
            
        self.high_price = max(self.high_price, price)
        self.low_price = min(self.low_price, price)
        self.close_price = price
        self.volume += volume
        self.trade_count += 1
    
    def to_candle(
        self,
        symbol: str,
        interval: str,
        candle_timestamp: int,
        tenant_id: str = "",
        exchange: str = "binance"
    ) -> Dict[str, Any]:
        """Convert buffer to candle dict"""
        return {
            "tenant_id": tenant_id,
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
            "timestamp": candle_timestamp,
            "open": self.open_price or 0,
            "high": self.high_price if self.high_price > 0 else 0,
            "low": self.low_price if self.low_price < float("inf") else 0,
            "close": self.close_price,
            "volume": self.volume,
            "trade_count": self.trade_count,
            "quote_volume": 0,
            "taker_buy_volume": 0,
            "taker_buy_quote_volume": 0,
        }
    
    def reset(self):
        """Reset the buffer"""
        self.open_price = None
        self.high_price = 0
        self.low_price = float("inf")
        self.close_price = 0
        self.volume = 0
        self.trade_count = 0
        self.first_timestamp = None


class CandleAggregationJob:
    """
    Aggregates tick data into OHLCV candles
    Supports multiple intervals: 1m, 5m, 15m, 30m, 1h, 4h, 1d
    """
    
    def __init__(
        self,
        intervals: List[str],
        output_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize candle aggregation job
        
        Args:
            intervals: List of intervals to aggregate (e.g., ['1m', '5m', '1h'])
            output_handler: Async function to call with completed candles
        """
        self.intervals = [i for i in intervals if i in INTERVAL_SECONDS]
        self.output_handler = output_handler
        
        # Buffers: symbol -> interval -> CandleBuffer
        self._buffers: Dict[str, Dict[str, CandleBuffer]] = defaultdict(
            lambda: {interval: CandleBuffer() for interval in self.intervals}
        )
        
        # Track current candle timestamps
        self._current_candle_ts: Dict[str, Dict[str, int]] = defaultdict(dict)
        
        self._candles_emitted = 0
        self._ticks_processed = 0
        self._running = False
        
        logger.info(f"CandleAggregationJob initialized for intervals: {self.intervals}")
    
    async def start(self):
        """Start the aggregation job"""
        self._running = True
        logger.info("✅ CandleAggregationJob started")
    
    async def stop(self):
        """Stop the job and emit remaining candles"""
        logger.info("Stopping CandleAggregationJob...")
        
        # Emit any remaining candles in buffers
        await self._emit_all_remaining()
        
        self._running = False
        logger.info(
            f"✅ CandleAggregationJob stopped. "
            f"Ticks: {self._ticks_processed}, Candles: {self._candles_emitted}"
        )
    
    async def process(self, data: Dict[str, Any]):
        """
        Process a tick and aggregate into candles
        
        Args:
            data: Market data tick
        """
        if not self._running:
            return
            
        try:
            symbol = data.get("symbol", "")
            price = float(data.get("price", 0))
            volume = float(data.get("volume", 0))
            timestamp = data.get("timestamp", 0)
            tenant_id = data.get("tenant_id", "")
            exchange = data.get("exchange", "binance")
            
            if not symbol or not price:
                return
            
            # Convert timestamp to seconds if in milliseconds
            if timestamp > 1e12:
                timestamp_s = timestamp // 1000
            else:
                timestamp_s = timestamp
            
            self._ticks_processed += 1
            
            # Process for each interval
            for interval in self.intervals:
                await self._process_for_interval(
                    symbol=symbol,
                    interval=interval,
                    price=price,
                    volume=volume,
                    timestamp_s=timestamp_s,
                    timestamp_ms=timestamp,
                    tenant_id=tenant_id,
                    exchange=exchange,
                )
                
        except Exception as e:
            logger.error(f"Error processing tick for candle: {e}", exc_info=True)
    
    async def _process_for_interval(
        self,
        symbol: str,
        interval: str,
        price: float,
        volume: float,
        timestamp_s: int,
        timestamp_ms: int,
        tenant_id: str,
        exchange: str,
    ):
        """Process tick for a specific interval"""
        interval_seconds = INTERVAL_SECONDS[interval]
        candle_ts = (timestamp_s // interval_seconds) * interval_seconds
        
        buffer = self._buffers[symbol][interval]
        current_ts = self._current_candle_ts[symbol].get(interval)
        
        # Check if we need to emit the current candle
        if current_ts is not None and candle_ts > current_ts:
            # Emit completed candle
            candle = buffer.to_candle(
                symbol=symbol,
                interval=interval,
                candle_timestamp=current_ts * 1000,  # Convert to ms
                tenant_id=tenant_id,
                exchange=exchange,
            )
            await self._emit_candle(candle)
            buffer.reset()
        
        # Update current candle timestamp
        self._current_candle_ts[symbol][interval] = candle_ts
        
        # Add tick to buffer
        buffer.add_tick(price, volume, timestamp_ms)
    
    async def _emit_candle(self, candle: Dict[str, Any]):
        """Emit a completed candle"""
        self._candles_emitted += 1
        
        logger.debug(
            f"Emitting candle: {candle['symbol']} {candle['interval']} "
            f"O:{candle['open']:.2f} H:{candle['high']:.2f} "
            f"L:{candle['low']:.2f} C:{candle['close']:.2f}"
        )
        
        if self.output_handler:
            try:
                await self.output_handler(candle)
            except Exception as e:
                logger.error(f"Error in candle output handler: {e}")
    
    async def _emit_all_remaining(self):
        """Emit all remaining candles in buffers"""
        for symbol, interval_buffers in self._buffers.items():
            for interval, buffer in interval_buffers.items():
                if buffer.trade_count > 0:
                    current_ts = self._current_candle_ts[symbol].get(interval, 0)
                    candle = buffer.to_candle(
                        symbol=symbol,
                        interval=interval,
                        candle_timestamp=current_ts * 1000,
                        tenant_id="",  # Unknown at this point
                        exchange="binance",
                    )
                    await self._emit_candle(candle)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job statistics"""
        buffer_stats = {}
        for symbol, interval_buffers in self._buffers.items():
            buffer_stats[symbol] = {
                interval: buffer.trade_count
                for interval, buffer in interval_buffers.items()
            }
        
        return {
            "job_type": "candle_aggregation",
            "intervals": self.intervals,
            "ticks_processed": self._ticks_processed,
            "candles_emitted": self._candles_emitted,
            "active_buffers": len(self._buffers),
            "buffer_details": buffer_stats,
            "is_running": self._running,
        }

