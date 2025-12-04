"""
ClickHouse Sink
Writes processed market data to ClickHouse tables
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from clickhouse_driver import Client

logger = logging.getLogger(__name__)

# Default UUID for records without tenant_id
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


class ClickHouseSink:
    """
    Sink for writing data to ClickHouse
    Handles batching and flush logic
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str = "default",
        password: str = "",
        batch_size: int = 100,
        flush_interval: int = 5,
    ):
        """
        Initialize ClickHouse sink
        
        Args:
            host: ClickHouse host
            port: ClickHouse port
            database: Database name
            user: Username
            password: Password
            batch_size: Number of records to batch before flush
            flush_interval: Seconds between automatic flushes
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.client: Optional[Client] = None
        self._market_data_buffer: List[Dict[str, Any]] = []
        self._candle_buffer: List[Dict[str, Any]] = []
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Metrics
        self._records_written = 0
        self._flush_count = 0
        self._errors = 0
        
        logger.info(f"ClickHouseSink initialized for {host}:{port}/{database}")
    
    async def start(self):
        """Start the ClickHouse sink"""
        logger.info("Starting ClickHouse sink...")
        
        self.client = Client(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )
        
        # Test connection
        result = self.client.execute("SELECT 1")
        logger.info(f"ClickHouse connection test: {result}")
        
        self._running = True
        
        # Start periodic flush task
        self._flush_task = asyncio.create_task(self._periodic_flush())
        
        logger.info("✅ ClickHouse sink started")
    
    async def stop(self):
        """Stop the sink and flush remaining data"""
        logger.info("Stopping ClickHouse sink...")
        
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush()
        
        if self.client:
            self.client.disconnect()
            
        logger.info(f"✅ ClickHouse sink stopped. Total records written: {self._records_written}")
    
    async def write_market_data(self, data: Dict[str, Any]):
        """
        Buffer market data for writing
        
        Args:
            data: Market data record
        """
        async with self._lock:
            self._market_data_buffer.append(data)
            
            if len(self._market_data_buffer) >= self.batch_size:
                await self._flush_market_data()
    
    async def write_candle(self, candle: Dict[str, Any]):
        """
        Buffer candle data for writing
        
        Args:
            candle: OHLCV candle record
        """
        async with self._lock:
            self._candle_buffer.append(candle)
            
            if len(self._candle_buffer) >= self.batch_size:
                await self._flush_candles()
    
    async def flush(self):
        """Flush all buffers to ClickHouse"""
        async with self._lock:
            await self._flush_market_data()
            await self._flush_candles()
    
    def _parse_uuid(self, value: Any) -> uuid.UUID:
        """Parse tenant_id to UUID, handling various formats"""
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str) and value:
            try:
                return uuid.UUID(value)
            except ValueError:
                logger.warning(f"Invalid UUID format: {value}, using default")
                return DEFAULT_TENANT_ID
        return DEFAULT_TENANT_ID
    
    async def _flush_market_data(self):
        """Flush market data buffer to ClickHouse"""
        if not self._market_data_buffer or not self.client:
            return
            
        records = self._market_data_buffer
        self._market_data_buffer = []
        
        try:
            # Prepare data for insert
            rows = []
            for record in records:
                rows.append((
                    self._parse_uuid(record.get("tenant_id")),
                    self._parse_timestamp(record.get("timestamp")),
                    record.get("symbol", ""),
                    record.get("exchange", "binance"),
                    float(record.get("price", 0)),
                    float(record.get("volume", 0)),
                    float(record.get("bid_price", 0)),
                    float(record.get("ask_price", 0)),
                    float(record.get("bid_volume", 0)),
                    float(record.get("ask_volume", 0)),
                    float(record.get("high_24h", 0)),
                    float(record.get("low_24h", 0)),
                    float(record.get("volume_24h", 0)),
                    float(record.get("price_change_24h", 0)),
                    float(record.get("price_change_pct_24h", 0)),
                    int(record.get("trade_count", 0)),
                    "",  # metadata
                ))
            
            # Insert into ClickHouse using tuple format
            self.client.execute(
                """
                INSERT INTO market_data (
                    tenant_id, timestamp, symbol, exchange, price, volume,
                    bid_price, ask_price, bid_volume, ask_volume,
                    high_24h, low_24h, volume_24h, price_change_24h,
                    price_change_pct_24h, trade_count, metadata
                ) VALUES
                """,
                rows
            )
            
            self._records_written += len(rows)
            self._flush_count += 1
            
            logger.debug(f"Flushed {len(rows)} market data records to ClickHouse")
            
        except Exception as e:
            self._errors += 1
            logger.error(f"Error flushing market data: {e}", exc_info=True)
            # Re-add to buffer for retry (max once)
            if len(self._market_data_buffer) == 0:
                self._market_data_buffer = records
    
    async def _flush_candles(self):
        """Flush candle buffer to ClickHouse"""
        if not self._candle_buffer or not self.client:
            return
            
        records = self._candle_buffer
        self._candle_buffer = []
        
        try:
            rows = []
            for candle in records:
                rows.append((
                    self._parse_uuid(candle.get("tenant_id")),
                    self._parse_timestamp(candle.get("timestamp")),
                    candle.get("symbol", ""),
                    candle.get("exchange", "binance"),
                    candle.get("interval", "1m"),
                    float(candle.get("open", 0)),
                    float(candle.get("high", 0)),
                    float(candle.get("low", 0)),
                    float(candle.get("close", 0)),
                    float(candle.get("volume", 0)),
                    float(candle.get("quote_volume", 0)),
                    int(candle.get("trade_count", 0)),
                    float(candle.get("taker_buy_volume", 0)),
                    float(candle.get("taker_buy_quote_volume", 0)),
                ))
            
            self.client.execute(
                """
                INSERT INTO market_candles (
                    tenant_id, timestamp, symbol, exchange, interval,
                    open, high, low, close, volume, quote_volume,
                    trade_count, taker_buy_volume, taker_buy_quote_volume
                ) VALUES
                """,
                rows
            )
            
            self._records_written += len(rows)
            
            logger.debug(f"Flushed {len(rows)} candles to ClickHouse")
            
        except Exception as e:
            self._errors += 1
            logger.error(f"Error flushing candles: {e}", exc_info=True)
            if len(self._candle_buffer) == 0:
                self._candle_buffer = records
    
    async def _periodic_flush(self):
        """Periodically flush buffers"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    def _parse_timestamp(self, ts) -> datetime:
        """Parse timestamp to datetime"""
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, (int, float)):
            # Assume milliseconds if > 1e12
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts)
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return datetime.utcnow()
        return datetime.utcnow()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sink statistics"""
        return {
            "records_written": self._records_written,
            "flush_count": self._flush_count,
            "errors": self._errors,
            "market_data_buffer_size": len(self._market_data_buffer),
            "candle_buffer_size": len(self._candle_buffer),
            "is_running": self._running,
        }
