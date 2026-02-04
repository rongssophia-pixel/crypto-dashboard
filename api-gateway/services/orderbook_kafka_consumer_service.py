"""
Kafka Consumer Service for Orderbook WebSocket Streaming
Consumes processed orderbook snapshots from Kafka and broadcasts to WS clients.
"""

import asyncio
import json
import logging
from ssl import create_default_context
from typing import Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from config import settings
from services.orderbook_connection_manager import OrderbookConnectionManager

logger = logging.getLogger(__name__)


class OrderbookWebSocketKafkaConsumer:
    def __init__(self, connection_manager: OrderbookConnectionManager):
        self.connection_manager = connection_manager
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._consume_task: Optional[asyncio.Task] = None

        logger.info("OrderbookWebSocketKafkaConsumer initialized")

    async def start(self):
        try:
            consumer_config = {
                "bootstrap_servers": settings.kafka_bootstrap_servers,
                "group_id": f"{settings.kafka_consumer_group}-orderbook",
                "auto_offset_reset": "latest",
                "enable_auto_commit": True,
                "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
                "security_protocol": settings.kafka_security_protocol,
                "connections_max_idle_ms": 540000,
                "session_timeout_ms": 45000,
                "heartbeat_interval_ms": 3000,
                "request_timeout_ms": 30000,
            }

            if settings.kafka_security_protocol == "SASL_SSL":
                consumer_config["sasl_mechanism"] = settings.kafka_sasl_mechanism
                consumer_config["sasl_plain_username"] = settings.kafka_sasl_username
                consumer_config["sasl_plain_password"] = settings.kafka_sasl_password
                consumer_config["ssl_context"] = create_default_context()

            self.consumer = AIOKafkaConsumer(
                settings.kafka_topic_processed_orderbook,
                **consumer_config,
            )

            await self.consumer.start()
            self._running = True

            logger.info(
                f"Orderbook Kafka consumer started: topic={settings.kafka_topic_processed_orderbook}, "
                f"bootstrap_servers={settings.kafka_bootstrap_servers}"
            )

        except Exception as e:
            logger.error(f"Failed to start orderbook Kafka consumer: {e}", exc_info=True)
            raise

    async def consume_loop(self):
        if not self.consumer:
            logger.error("Cannot start consume loop: consumer not initialized")
            return

        retry_count = 0
        max_retries = 5

        while self._running:
            try:
                async for message in self.consumer:
                    if not self._running:
                        break
                    try:
                        data = message.value
                        symbol = data.get("symbol")
                        if not symbol:
                            continue

                        ws_message = self._format_orderbook_message(data)
                        await self.connection_manager.broadcast_to_symbol(symbol, ws_message)

                        retry_count = 0
                    except Exception as e:
                        logger.error(f"Error processing orderbook Kafka message: {e}", exc_info=True)

            except KafkaError as e:
                logger.error(f"Kafka error in orderbook consume loop: {e}", exc_info=True)
                retry_count += 1
                if retry_count >= max_retries:
                    self._running = False
                    break
                await asyncio.sleep(min(2 ** retry_count, 60))

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Unexpected error in orderbook consume loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    def _format_orderbook_message(self, data: dict) -> dict:
        return {
            "type": "orderbook",
            "symbol": data.get("symbol"),
            "exchange": data.get("exchange"),
            "timestamp": data.get("timestamp"),
            "levels": data.get("levels"),
            "bids": data.get("bids") or [],
            "asks": data.get("asks") or [],
            "last_update_id": data.get("last_update_id"),
            "processed_at": data.get("processed_at"),
            "mid_price": data.get("mid_price"),
            "spread": data.get("spread"),
            "spread_pct": data.get("spread_pct"),
        }

    async def stop(self):
        self._running = False
        if self._consume_task and not self._consume_task.done():
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
        if self.consumer:
            await self.consumer.stop()

    def get_stats(self) -> dict:
        return {
            "running": self._running,
            "topic": settings.kafka_topic_processed_orderbook,
            "group_id": f"{settings.kafka_consumer_group}-orderbook",
        }


