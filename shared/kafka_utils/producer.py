"""
Kafka Producer Wrapper
Provides a simplified interface for publishing messages to Kafka topics
"""

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from kafka import KafkaProducer

logger = logging.getLogger(__name__)


class KafkaProducerWrapper:
    """Wrapper around Kafka producer with JSON serialization"""

    def __init__(
        self,
        bootstrap_servers: str,
        client_id: Optional[str] = None,
        compression_type: str = "gzip",
        acks: str = "all",
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: Optional[str] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            client_id=client_id,
            compression_type=compression_type,
            acks=acks,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            retries=3,
            max_in_flight_requests_per_connection=5,
            request_timeout_ms=30000,
            security_protocol=security_protocol,
            sasl_mechanism=sasl_mechanism,
            sasl_plain_username=sasl_plain_username,
            sasl_plain_password=sasl_plain_password,
        )
        logger.info(f"Kafka producer initialized: {bootstrap_servers}")

    def send(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        callback: Optional[Callable] = None,
    ):
        """Send a message to a Kafka topic"""
        try:
            # Add timestamp if not present
            if "timestamp" not in value:
                value["timestamp"] = datetime.utcnow().isoformat()

            # Convert headers to bytes if provided
            kafka_headers = None
            if headers:
                kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

            # Send message
            future = self.producer.send(
                topic, value=value, key=key, partition=partition, headers=kafka_headers
            )

            # Add callback if provided
            if callback:
                future.add_callback(callback)
                future.add_errback(lambda e: logger.error(f"Message failed: {e}"))

            return future

        except Exception as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            raise

    def send_batch(
        self,
        topic: str,
        messages: list[Dict[str, Any]],
        keys: Optional[list[str]] = None,
    ) -> list:
        """Send a batch of messages to a topic"""
        futures = []
        for i, msg in enumerate(messages):
            key = keys[i] if keys and i < len(keys) else None
            future = self.send(topic, msg, key=key)
            futures.append(future)

        return futures

    def flush(self, timeout: Optional[int] = None):
        """Flush pending messages"""
        self.producer.flush(timeout=timeout)

    def close(self):
        """Close the producer"""
        self.producer.close()
        logger.info("Kafka producer closed")


class MarketDataProducer:
    """Specialized producer for market data messages"""

    def __init__(self, producer: KafkaProducerWrapper, topic: str):
        self.producer = producer
        self.topic = topic
        logger.info(f"MarketDataProducer initialized for topic: {topic}")

    def publish_market_data(
        self,
        tenant_id: str,
        symbol: str,
        price: float,
        volume: float,
        timestamp: int,
        exchange: str = "binance",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Publish market data message"""
        message = {
            "tenant_id": tenant_id,
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "timestamp": timestamp,
            "exchange": exchange,
            "metadata": metadata or {},
        }

        # Use symbol as key for partitioning
        return self.producer.send(topic=self.topic, value=message, key=symbol)


# TODO: Implement Kafka producer wrapper
# TODO: Add automatic retry logic
# TODO: Add message delivery confirmation
# TODO: Add metrics for monitoring
# TODO: Add support for Avro/Protobuf serialization
