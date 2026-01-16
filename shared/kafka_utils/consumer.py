"""
Kafka Consumer Wrapper
Provides a simplified interface for consuming messages from Kafka topics
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException

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
        session_timeout_ms: int = 45000,  # Increased for Confluent Cloud
        max_poll_interval_ms: int = 300000,
        heartbeat_interval_ms: int = 3000,
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: Optional[str] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
    ):
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self._running = False
        
        # Build configuration dict for confluent_kafka
        config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': enable_auto_commit,
            'session.timeout.ms': session_timeout_ms,
            'max.poll.interval.ms': max_poll_interval_ms,
            'heartbeat.interval.ms': heartbeat_interval_ms,
            # Important for Confluent Cloud stability
            'socket.keepalive.enable': True,
        }
        
        # Add SASL configuration if needed
        if security_protocol == "SASL_SSL":
            config['security.protocol'] = 'SASL_SSL'
            config['sasl.mechanism'] = sasl_mechanism or 'PLAIN'
            config['sasl.username'] = sasl_plain_username
            config['sasl.password'] = sasl_plain_password
        
        self.consumer = Consumer(config)
        self.consumer.subscribe(topics)
        logger.info(f"Kafka consumer created: {group_id} subscribed to {topics}")

    def consume(
        self,
        handler: Callable[[Dict[str, Any]], None],
        max_messages: Optional[int] = None,
    ):
        """
        Consume messages and process with handler.
        This is a blocking call - run in a thread for async usage.
        """
        message_count = 0
        self._running = True

        try:
            while self._running:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, not an error
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        raise KafkaException(msg.error())
                
                try:
                    # Deserialize message
                    value = json.loads(msg.value().decode('utf-8'))
                    handler(value)
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
        messages = []

        try:
            for _ in range(batch_size):
                msg = self.consumer.poll(timeout=timeout_ms / 1000.0)
                
                if msg is None:
                    break
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break
                
                try:
                    value = json.loads(msg.value().decode('utf-8'))
                    messages.append(value)
                except Exception as e:
                    logger.error(f"Error deserializing message: {e}")

        except Exception as e:
            logger.error(f"Error consuming batch: {e}")

        return messages

    def commit(self):
        """Manually commit current offsets"""
        self.consumer.commit(asynchronous=False)

    def close(self):
        """Close the consumer"""
        self._running = False
        self.consumer.close()
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
