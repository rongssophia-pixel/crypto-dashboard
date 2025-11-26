"""
Kafka Consumer Wrapper
Provides a simplified interface for consuming messages from Kafka topics
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from kafka import KafkaConsumer

logger = logging.getLogger(__name__)


class KafkaConsumerWrapper:
    """Wrapper around Kafka consumer with JSON deserialization"""

    def __init__(
        self,
        topics: List[str],
        bootstrap_servers: str,
        group_id: str,
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True,
    ):
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers.split(","),
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=enable_auto_commit,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )
        logger.info(f"Kafka consumer initialized: {group_id} subscribed to {topics}")

    def consume(
        self,
        handler: Callable[[Dict[str, Any]], None],
        max_messages: Optional[int] = None,
        timeout_ms: int = 1000,
    ):
        """Consume messages and process with handler"""
        message_count = 0

        try:
            for message in self.consumer:
                try:
                    # Process message
                    handler(message.value)
                    message_count += 1

                    if max_messages and message_count >= max_messages:
                        break

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    # Continue processing other messages

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        finally:
            logger.info(f"Processed {message_count} messages")

    def consume_batch(
        self, batch_size: int = 100, timeout_ms: int = 1000
    ) -> List[Dict[str, Any]]:
        """Consume a batch of messages"""
        messages = []

        try:
            for message in self.consumer:
                messages.append(message.value)

                if len(messages) >= batch_size:
                    break

        except Exception as e:
            logger.error(f"Error consuming batch: {e}")

        return messages

    def commit(self):
        """Manually commit current offsets"""
        self.consumer.commit()

    def close(self):
        """Close the consumer"""
        self.consumer.close()
        logger.info("Kafka consumer closed")


class MarketDataConsumer:
    """Specialized consumer for market data messages"""

    def __init__(
        self,
        consumer: KafkaConsumerWrapper,
        message_handler: Callable[[Dict[str, Any]], None],
    ):
        self.consumer = consumer
        self.message_handler = message_handler
        self.running = False

    def start(self):
        """Start consuming market data messages"""
        self.running = True
        logger.info("MarketDataConsumer started")

        try:
            self.consumer.consume(self.message_handler)
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise

    def stop(self):
        """Stop consuming messages"""
        self.running = False
        self.consumer.close()
        logger.info("MarketDataConsumer stopped")


# TODO: Implement Kafka consumer wrapper
# TODO: Add automatic error handling and retry
# TODO: Add dead letter queue for failed messages
# TODO: Add metrics for monitoring
# TODO: Add support for Avro/Protobuf deserialization
