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
        tenant_id: str,
        symbol: str,
        exchange: str,
        data: Dict[str, Any],
        topic: str,
    ) -> bool:
        """Publish market data to Kafka topic"""
        try:
            # Enrich data with tenant context
            enriched_data = {
                **data,
                "tenant_id": tenant_id,
                "symbol": symbol,
                "exchange": exchange,
            }

            # Publish to Kafka with symbol as key for partitioning
            future = self.producer.send(topic=topic, value=enriched_data, key=symbol)

            # Wait for confirmation
            future.get(timeout=10)
            return True

        except Exception as e:
            logger.error(f"Failed to publish market data: {e}")
            return False

    async def publish_batch(self, messages: list[Dict[str, Any]], topic: str) -> int:
        """Publish batch of messages to Kafka"""
        success_count = 0

        for msg in messages:
            try:
                future = self.producer.send(
                    topic=topic, value=msg, key=msg.get("symbol")
                )
                future.get(timeout=10)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to publish message: {e}")

        return success_count

    def close(self):
        """Close the Kafka producer"""
        self.producer.close()


# TODO: Add retry logic for failed publishes
# TODO: Add metrics for publish latency
# TODO: Add dead letter queue for failed messages
# TODO: Add schema validation before publishing
