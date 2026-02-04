"""
Kafka Consumer Service for WebSocket Streaming
Consumes market data from Kafka and broadcasts to WebSocket clients
"""

import asyncio
import json
import logging
from ssl import create_default_context
from typing import Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from config import settings
from services.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)


class WebSocketKafkaConsumer:
    """
    Consumes from crypto.processed.market-data and broadcasts to WebSocket clients
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize Kafka consumer
        
        Args:
            connection_manager: WebSocket connection manager instance
        """
        self.connection_manager = connection_manager
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._consume_task: Optional[asyncio.Task] = None
        
        logger.info("WebSocketKafkaConsumer initialized")
    
    async def start(self):
        """Initialize and start the Kafka consumer"""
        try:
            # Build consumer configuration
            consumer_config = {
                "bootstrap_servers": settings.kafka_bootstrap_servers,
                "group_id": settings.kafka_consumer_group,
                "auto_offset_reset": "latest",  # Start from latest messages
                "enable_auto_commit": True,
                "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
                "security_protocol": settings.kafka_security_protocol,
                # Connection settings for Confluent Cloud stability
                "connections_max_idle_ms": 540000,  # 9 minutes
                "session_timeout_ms": 45000,  # 45 seconds (increased for cloud)
                "heartbeat_interval_ms": 3000,  # 3 seconds
                "request_timeout_ms": 30000,  # 30 seconds
            }
            
            # Add SASL configuration if needed
            if settings.kafka_security_protocol == "SASL_SSL":
                consumer_config["sasl_mechanism"] = settings.kafka_sasl_mechanism
                consumer_config["sasl_plain_username"] = settings.kafka_sasl_username
                consumer_config["sasl_plain_password"] = settings.kafka_sasl_password
                consumer_config["ssl_context"] = create_default_context()
            
            self.consumer = AIOKafkaConsumer(
                settings.kafka_topic_processed_market_data,
                **consumer_config
            )
            
            await self.consumer.start()
            self._running = True
            
            logger.info(
                f"Kafka consumer started: topic={settings.kafka_topic_processed_market_data}, "
                f"bootstrap_servers={settings.kafka_bootstrap_servers}, "
                f"group_id={settings.kafka_consumer_group}, "
                f"security_protocol={settings.kafka_security_protocol}"
            )
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}", exc_info=True)
            raise
    
    async def consume_loop(self):
        """
        Main consumer loop - consume messages and broadcast to WebSocket clients
        """
        if not self.consumer:
            logger.error("Cannot start consume loop: consumer not initialized")
            return
        
        logger.info("Starting Kafka consume loop...")
        
        retry_count = 0
        max_retries = 5
        
        while self._running:
            try:
                async for message in self.consumer:
                    if not self._running:
                        break
                    
                    try:
                        # Parse message data
                        data = message.value
                        symbol = data.get("symbol")
                        
                        if not symbol:
                            logger.warning("Received message without symbol")
                            continue
                        
                        # Prepare message for WebSocket clients
                        ws_message = self._format_market_data_message(data)
                        
                        # Broadcast to all subscribers of this symbol
                        await self.connection_manager.broadcast_to_symbol(
                            symbol, ws_message
                        )
                        
                        # Reset retry count on successful processing
                        retry_count = 0
                        
                    except Exception as e:
                        logger.error(f"Error processing Kafka message: {e}", exc_info=True)
                        continue
                
            except KafkaError as e:
                logger.error(f"Kafka error in consume loop: {e}", exc_info=True)
                retry_count += 1
                
                if retry_count >= max_retries:
                    logger.error(
                        f"Max retries ({max_retries}) reached. Stopping consumer."
                    )
                    self._running = False
                    break
                
                # Exponential backoff
                wait_time = min(2 ** retry_count, 60)
                logger.info(f"Retrying in {wait_time} seconds... (attempt {retry_count})")
                await asyncio.sleep(wait_time)
                
            except asyncio.CancelledError:
                logger.info("Consume loop cancelled")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error in consume loop: {e}", exc_info=True)
                await asyncio.sleep(5)
        
        logger.info("Kafka consume loop stopped")
    
    def _format_market_data_message(self, data: dict) -> dict:
        """
        Format Kafka message data for WebSocket clients
        
        Args:
            data: Raw message data from Kafka
            
        Returns:
            Formatted message dict
        """
        # Convert Decimal/datetime to strings if present
        formatted = {
            "type": "market_data",
            "symbol": data.get("symbol"),
            "exchange": data.get("exchange"),
            "timestamp": data.get("timestamp"),
            "price": float(data.get("price", 0)) if data.get("price") else None,
            "volume": float(data.get("volume", 0)) if data.get("volume") else None,
            "bid_price": float(data.get("bid_price", 0)) if data.get("bid_price") else None,
            "ask_price": float(data.get("ask_price", 0)) if data.get("ask_price") else None,
            "bid_volume": float(data.get("bid_volume", 0)) if data.get("bid_volume") else None,
            "ask_volume": float(data.get("ask_volume", 0)) if data.get("ask_volume") else None,
        }
        
        # Add optional enriched fields if present
        if "spread" in data:
            formatted["spread"] = float(data["spread"])
        if "spread_pct" in data:
            formatted["spread_pct"] = float(data["spread_pct"])
        if "mid_price" in data:
            formatted["mid_price"] = float(data["mid_price"])
        
        # Add 24h statistics if present
        if "open_24h" in data and data["open_24h"]:
            formatted["open_24h"] = float(data["open_24h"])
        if "high_24h" in data and data["high_24h"]:
            formatted["high_24h"] = float(data["high_24h"])
        if "low_24h" in data and data["low_24h"]:
            formatted["low_24h"] = float(data["low_24h"])
        if "volume_24h" in data and data["volume_24h"]:
            formatted["volume_24h"] = float(data["volume_24h"])
        if "price_change_24h" in data and data["price_change_24h"]:
            formatted["price_change_24h"] = float(data["price_change_24h"])
        if "price_change_pct_24h" in data and data["price_change_pct_24h"]:
            formatted["price_change_pct_24h"] = float(data["price_change_pct_24h"])
        
        return formatted
    
    async def stop(self):
        """Stop the Kafka consumer"""
        logger.info("Stopping Kafka consumer...")
        self._running = False
        
        # Cancel consume task if running
        if self._consume_task and not self._consume_task.done():
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
        
        # Stop and close consumer
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}", exc_info=True)
    
    def get_stats(self) -> dict:
        """
        Get consumer statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            "running": self._running,
            "topic": settings.kafka_topic_processed_market_data,
            "group_id": settings.kafka_consumer_group,
            "bootstrap_servers": settings.kafka_bootstrap_servers,
        }
