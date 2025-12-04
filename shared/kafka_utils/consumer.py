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
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self._running = False
        self.consumer: Optional[KafkaConsumer] = None
        
    def _create_consumer(self):
        """Create the Kafka consumer instance"""
        self.consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers.split(","),
            group_id=self.group_id,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=self.enable_auto_commit,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
            consumer_timeout_ms=1000,  # Allow checking _running flag
        )
        logger.info(f"Kafka consumer created: {self.group_id} subscribed to {self.topics}")

    def consume(
        self,
        handler: Callable[[Dict[str, Any]], None],
        max_messages: Optional[int] = None,
    ):
        """
        Consume messages and process with handler.
        This is a blocking call - run in a thread for async usage.
        """
        if not self.consumer:
            self._create_consumer()
            
        message_count = 0
        self._running = True

        try:
            while self._running:
                # Poll with timeout to allow checking _running flag
                messages = self.consumer.poll(timeout_ms=1000)
                
                for tp, records in messages.items():
                    for message in records:
                        if not self._running:
                            break
                        try:
                            handler(message.value)
                            message_count += 1

                            if max_messages and message_count >= max_messages:
                                self._running = False
                                break

                        except Exception as e:
                            logger.error(f"Error processing message: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Consumer error: {e}", exc_info=True)
        finally:
            logger.info(f"Processed {message_count} messages")

    def consume_batch(
        self, batch_size: int = 100, timeout_ms: int = 1000
    ) -> List[Dict[str, Any]]:
        """Consume a batch of messages"""
        if not self.consumer:
            self._create_consumer()
            
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
        if self.consumer:
            self.consumer.commit()

    def close(self):
        """Close the consumer"""
        self._running = False
        if self.consumer:
            self.consumer.close()
            self.consumer = None
        logger.info("Kafka consumer closed")
    
    @property
    def is_running(self) -> bool:
        """Check if consumer is running"""
        return self._running


class MarketDataConsumer:
    """Specialized consumer for market data messages"""

    def __init__(
        self,
        consumer: KafkaConsumerWrapper,
        message_handler: Callable[[Dict[str, Any]], None],
    ):
        self.consumer = consumer
        self.message_handler = message_handler

    def start(self):
        """Start consuming market data messages (blocking)"""
        logger.info("MarketDataConsumer started")

        try:
            self.consumer.consume(self.message_handler)
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise

    def stop(self):
        """Stop consuming messages"""
        self.consumer.close()
        logger.info("MarketDataConsumer stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if consumer is running"""
        return self.consumer.is_running


# TODO: Add automatic error handling and retry
# TODO: Add dead letter queue for failed messages
# TODO: Add metrics for monitoring
# TODO: Add support for Avro/Protobuf deserialization
