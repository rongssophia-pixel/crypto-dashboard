"""
Ingestion Business Service
Core business logic for automatic data ingestion
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IngestionBusinessService:
    """Business logic for automatic ingestion operations"""

    def __init__(self, kafka_repository, binance_connector):
        """
        Initialize ingestion service

        Args:
            kafka_repository: Repository for publishing to Kafka
            binance_connector: Binance WebSocket connector
        """
        self.kafka_repository = kafka_repository
        self.binance_connector = binance_connector
        self.active_connections: List[str] = []  # List of WebSocket connection IDs
        self.symbol_list: List[str] = []
        self.refresh_task: Optional[asyncio.Task] = None
        logger.info("IngestionBusinessService initialized")

    async def start_auto_ingestion(
        self,
        intervals: List[str],
        quote_currency: str,
        enable_ticker: bool,
        max_symbols_per_connection: int,
        kafka_topic: str,
    ) -> Dict[str, Any]:
        """
        Start automatic ingestion for all trading pairs

        Args:
            intervals: List of kline intervals to subscribe to
            quote_currency: Filter symbols by quote currency
            enable_ticker: Whether to enable ticker streams
            max_symbols_per_connection: Max symbols per WebSocket connection
            kafka_topic: Kafka topic to publish to

        Returns:
            Status information
        """
        try:
            logger.info("=" * 60)
            logger.info("🚀 Starting automatic ingestion...")
            logger.info("=" * 60)

            # 1. Fetch all trading symbols
            logger.info(f"Fetching all {quote_currency} trading pairs...")
            symbols = await self.binance_connector.get_all_trading_symbols(
                quote_currency=quote_currency
            )

            if not symbols:
                logger.error("No trading symbols found. Cannot start ingestion.")
                return {
                    "success": False,
                    "error": "No trading symbols found",
                }

            self.symbol_list = symbols
            logger.info(f"✅ Found {len(symbols)} trading pairs")

            # 2. Create callbacks for data handling
            async def handle_kline_data(data):
                await self._handle_market_data(data, "kline", kafka_topic)

            async def handle_ticker_data(data):
                await self._handle_market_data(data, "ticker", kafka_topic)

            # 3. Start all streams with connection pooling
            logger.info(
                f"Starting streams: {len(intervals)} kline intervals, "
                f"ticker={'enabled' if enable_ticker else 'disabled'}"
            )

            connection_ids = await self.binance_connector.start_all_streams(
                symbols=symbols,
                intervals=intervals,
                kline_callback=handle_kline_data,
                ticker_callback=handle_ticker_data if enable_ticker else None,
                max_symbols_per_connection=max_symbols_per_connection,
            )

            self.active_connections = connection_ids

            logger.info("=" * 60)
            logger.info("✅ Automatic ingestion started successfully!")
            logger.info(f"   - Symbols: {len(symbols)}")
            logger.info(f"   - Intervals: {', '.join(intervals)}")
            logger.info(f"   - Ticker streams: {'enabled' if enable_ticker else 'disabled'}")
            logger.info(f"   - WebSocket connections: {len(connection_ids)}")
            logger.info("=" * 60)

            return {
                "success": True,
                "symbols_count": len(symbols),
                "intervals": intervals,
                "ticker_enabled": enable_ticker,
                "connections": len(connection_ids),
                "started_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to start automatic ingestion: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def start_symbol_refresh_task(
        self,
        refresh_interval_hours: int,
        intervals: List[str],
        quote_currency: str,
        enable_ticker: bool,
        max_symbols_per_connection: int,
        kafka_topic: str,
    ):
        """
        Start background task to periodically refresh symbol list

        Args:
            refresh_interval_hours: How often to refresh (in hours)
            intervals: Kline intervals
            quote_currency: Quote currency filter
            enable_ticker: Enable ticker streams
            max_symbols_per_connection: Max symbols per connection
            kafka_topic: Kafka topic
        """
        logger.info(
            f"Starting symbol refresh task (every {refresh_interval_hours} hours)"
        )

        async def refresh_loop():
            while True:
                try:
                    # Wait for refresh interval
                    await asyncio.sleep(refresh_interval_hours * 3600)

                    logger.info("🔄 Refreshing symbol list...")

                    # Fetch new symbol list
                    new_symbols = await self.binance_connector.get_all_trading_symbols(
                        quote_currency=quote_currency
                    )

                    # Check if symbols changed
                    added = set(new_symbols) - set(self.symbol_list)
                    removed = set(self.symbol_list) - set(new_symbols)

                    if added or removed:
                        logger.info(
                            f"Symbol list changed: +{len(added)} added, -{len(removed)} removed"
                        )

                        # Stop all existing streams
                        logger.info("Stopping existing streams...")
                        for conn_id in self.active_connections:
                            try:
                                await self.binance_connector.stop_stream(conn_id)
                            except Exception as e:
                                logger.error(f"Error stopping stream {conn_id}: {e}")

                        # Restart with new symbol list
                        logger.info("Restarting streams with updated symbol list...")
                        await self.start_auto_ingestion(
                            intervals=intervals,
                            quote_currency=quote_currency,
                            enable_ticker=enable_ticker,
                            max_symbols_per_connection=max_symbols_per_connection,
                            kafka_topic=kafka_topic,
                        )
                    else:
                        logger.info("✅ Symbol list unchanged")

                except Exception as e:
                    logger.error(f"Error in symbol refresh task: {e}", exc_info=True)

        self.refresh_task = asyncio.create_task(refresh_loop())

    async def stop_auto_ingestion(self):
        """Stop all active streams and background tasks"""
        logger.info("Stopping automatic ingestion...")

        # Stop refresh task
        if self.refresh_task:
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass

        # Stop all WebSocket connections
        for conn_id in self.active_connections:
            try:
                await self.binance_connector.stop_stream(conn_id)
            except Exception as e:
                logger.error(f"Error stopping stream {conn_id}: {e}")

        self.active_connections = []
        logger.info("✅ Automatic ingestion stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current ingestion status"""
        return {
            "active_connections": len(self.active_connections),
            "symbols_count": len(self.symbol_list),
            "symbols": self.symbol_list[:10],  # First 10 for preview
            "is_running": len(self.active_connections) > 0,
        }

    async def _handle_market_data(
        self, data: Dict[str, Any], data_type: str, kafka_topic: str
    ):
        """
        Handle incoming market data and publish to Kafka

        Args:
            data: Raw data from WebSocket
            data_type: Type of data (kline, ticker, trade)
            kafka_topic: Kafka topic to publish to
        """
        try:
            # Extract symbol from data
            # For combined streams, data structure is: {"stream": "btcusdt@kline_1m", "data": {...}}
            if "stream" in data and "data" in data:
                stream_name = data["stream"]
                inner_data = data["data"]
                
                # Determine type from stream name
                if "@kline_" in stream_name:
                    normalized = self._normalize_kline(inner_data)
                elif "@ticker" in stream_name:
                    normalized = self._normalize_ticker(inner_data)
                else:
                    logger.warning(f"Unknown stream type: {stream_name}")
                    return
            else:
                # Direct stream (not combined)
                if data_type == "kline":
                    normalized = self._normalize_kline(data)
                elif data_type == "ticker":
                    normalized = self._normalize_ticker(data)
                else:
                    logger.warning(f"Unknown data type: {data_type}")
                    return

            # Publish to Kafka
            symbol = normalized.get("symbol", "UNKNOWN")
            success = await self.kafka_repository.publish_market_data(
                symbol=symbol,
                exchange="binance",
                data=normalized,
                topic=kafka_topic,
            )

            if not success:
                logger.error(f"Failed to publish {data_type} data for {symbol}")

        except Exception as e:
            logger.error(f"Error handling market data: {e}", exc_info=True)

    def _normalize_kline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize kline data to standard format"""
        kline = data.get("k", {})
        return {
            "type": "kline",
            "symbol": kline.get("s"),
            "interval": kline.get("i"),
            "timestamp": kline.get("t"),
            "open": float(kline.get("o", 0)),
            "high": float(kline.get("h", 0)),
            "low": float(kline.get("l", 0)),
            "close": float(kline.get("c", 0)),
            "volume": float(kline.get("v", 0)),
            "close_time": kline.get("T"),
            "quote_volume": float(kline.get("q", 0)),
            "trade_count": int(kline.get("n", 0)),
            "taker_buy_volume": float(kline.get("V", 0)),
            "taker_buy_quote_volume": float(kline.get("Q", 0)),
            "is_closed": kline.get("x", False),
            "exchange": "binance",
        }

    def _normalize_ticker(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize ticker data to standard format"""
        return {
            "type": "ticker",
            "symbol": data.get("s"),
            "price": float(data.get("c", 0)),
            "volume": float(data.get("v", 0)),
            "bid_price": float(data.get("b", 0)),
            "ask_price": float(data.get("a", 0)),
            "bid_volume": float(data.get("B", 0)),
            "ask_volume": float(data.get("A", 0)),
            "high_24h": float(data.get("h", 0)),
            "low_24h": float(data.get("l", 0)),
            "volume_24h": float(data.get("v", 0)),
            "price_change_24h": float(data.get("p", 0)),
            "price_change_pct_24h": float(data.get("P", 0)),
            "trade_count": int(data.get("n", 0)),
            "timestamp": data.get("E", int(datetime.now().timestamp() * 1000)),
            "exchange": "binance",
        }
