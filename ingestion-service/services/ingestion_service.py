"""
Ingestion Business Service
Core business logic for data ingestion
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class IngestionBusinessService:
    """Business logic for ingestion operations"""

    def __init__(self, stream_repository, kafka_repository, binance_connector):
        self.stream_repository = stream_repository
        self.kafka_repository = kafka_repository
        self.binance_connector = binance_connector
        self.active_streams = {}  # stream_id -> {symbols, task}
        logger.info("IngestionBusinessService initialized")

    async def start_stream(
        self,
        symbols: List[str],
        exchange: str,
        stream_type: str,
        kafka_topic: str,
    ) -> Dict[str, Any]:
        """Start streaming market data for given symbols"""
        try:
            # Generate unique stream ID
            stream_id = str(uuid.uuid4())

            # Create stream session in database
            await self.stream_repository.create_stream(
                stream_id=stream_id,
                symbols=symbols,
                exchange=exchange,
                stream_type=stream_type,
            )

            # Create callback for market data
            async def data_callback(data):
                await self._handle_market_data(
                    data=data,
                    stream_id=stream_id,
                    kafka_topic=kafka_topic,
                )

            # Start connector websocket based on stream type
            if stream_type == "ticker":
                connector_stream_id = await self.binance_connector.start_ticker_stream(
                    symbols, data_callback
                )
            elif stream_type == "trade":
                connector_stream_id = await self.binance_connector.start_trade_stream(
                    symbols, data_callback
                )
            elif stream_type == "kline":
                # Default to 1m interval
                connector_stream_id = await self.binance_connector.start_kline_stream(
                    symbols, "1m", data_callback
                )
            else:
                raise ValueError(f"Unknown stream type: {stream_type}")

            # Track active stream
            self.active_streams[stream_id] = {
                "symbols": symbols,
                "exchange": exchange,
                "stream_type": stream_type,
                "connector_stream_id": connector_stream_id,
                "started_at": datetime.utcnow(),
            }

            logger.info(f"Started stream {stream_id}")

            return {
                "stream_id": stream_id,
                "status": "active",
                "symbols": symbols,
                "exchange": exchange,
                "stream_type": stream_type,
                "started_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to start stream: {e}", exc_info=True)
            raise

    async def stop_stream(self, stream_id: str) -> bool:
        """Stop an active data stream"""
        try:
            # Verify stream exists
            if stream_id not in self.active_streams:
                logger.warning(f"Stream not found: {stream_id}")
                return False

            stream_info = self.active_streams[stream_id]

            # Stop connector websocket
            connector_stream_id = stream_info["connector_stream_id"]
            await self.binance_connector.stop_stream(connector_stream_id)

            # Update database
            await self.stream_repository.stop_stream(stream_id)

            # Remove from active streams
            del self.active_streams[stream_id]

            logger.info(f"Stopped stream {stream_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop stream: {e}")
            return False

    async def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """Get status of a running stream"""
        try:
            # Get from database
            db_stream = await self.stream_repository.get_stream(stream_id)

            if not db_stream:
                return {"error": "Stream not found"}

            # Check if still active in memory
            is_active = stream_id in self.active_streams

            return {
                "stream_id": stream_id,
                "is_active": is_active,
                "symbols": db_stream["symbols"],
                "exchange": db_stream["exchange"],
                "stream_type": db_stream["stream_type"],
                "status": db_stream["status"],
                "events_processed": db_stream["events_processed"],
                "started_at": (
                    db_stream["started_at"].isoformat()
                    if db_stream["started_at"]
                    else None
                ),
                "last_event_at": (
                    db_stream["last_event_at"].isoformat()
                    if db_stream["last_event_at"]
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get stream status: {e}")
            return {"error": str(e)}

    async def fetch_historical_data(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Fetch historical market data"""
        try:
            # Convert datetime to milliseconds
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)

            # Fetch from Binance
            candles = await self.binance_connector.fetch_historical_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_ms,
                end_time=end_ms,
                limit=limit,
            )

            # Enrich with exchange info
            for candle in candles:
                candle["exchange"] = exchange

            logger.info(f"Fetched {len(candles)} historical candles for {symbol}")
            return candles

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return []

    async def _handle_market_data(
        self, data: Dict[str, Any], stream_id: str, kafka_topic: str
    ):
        """Handle incoming market data from connector"""
        try:
            # Publish to Kafka
            success = await self.kafka_repository.publish_market_data(
                symbol=data.get("symbol"),
                exchange=data.get("exchange", "binance"),
                data=data,
                topic=kafka_topic,
            )

            if success:
                # Update stream metrics
                await self.stream_repository.increment_event_count(stream_id)
            else:
                logger.error(f"Failed to publish data for stream {stream_id}")

        except Exception as e:
            logger.error(f"Error handling market data: {e}", exc_info=True)
