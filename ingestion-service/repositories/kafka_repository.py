"""
Kafka Repository
Handles Kafka producer operations for publishing market data
"""

import logging
from typing import Any, Dict

from shared.kafka_utils.producer import KafkaProducerWrapper

logger = logging.getLogger(__name__)


class KafkaRepository:
    """Repository for Kafka operations"""

    def __init__(self, producer: KafkaProducerWrapper):
        self.producer = producer
        logger.info("KafkaRepository initialized")

    async def publish_market_data(
        self,
        symbol: str,
        exchange: str,
        data: Dict[str, Any],
        topic: str,
    ) -> bool:
        """Publish market data to Kafka topic"""
        try:
            # Enrich data (no tenant_id)
            enriched_data = {
                **data,
                "symbol": symbol,
                "exchange": exchange,
            }

            # Publish to Kafka with symbol as key for partitioning
            # Note: confluent_kafka Producer.produce() doesn't return a future
            # It uses callbacks for delivery confirmation
            self.producer.send(topic=topic, value=enriched_data, key=symbol)
            
            # Flush to ensure message is sent (non-blocking with timeout=0)
            self.producer.flush(timeout=0)
            return True

        except Exception as e:
            logger.error(f"Failed to publish market data: {e}")
            return False

    async def publish_batch(self, messages: list[Dict[str, Any]], topic: str) -> int:
        """Publish batch of messages to Kafka"""
        success_count = 0

        for msg in messages:
            try:
                self.producer.send(
                    topic=topic, value=msg, key=msg.get("symbol")
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to publish message: {e}")

        # Flush all messages
        self.producer.flush(timeout=10)
        return success_count

    def close(self):
        """Close the Kafka producer"""
        self.producer.close()
