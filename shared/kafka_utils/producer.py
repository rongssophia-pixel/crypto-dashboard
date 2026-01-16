"""
Kafka Producer Wrapper
Provides a simplified interface for publishing messages to Kafka topics
"""

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from confluent_kafka import Producer

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
        
        # Build configuration dict for confluent_kafka
        config = {
            'bootstrap.servers': bootstrap_servers,
            'compression.type': compression_type,
            'acks': acks,
            'client.id': client_id or 'producer',
            'retries': 3,
            'request.timeout.ms': 30000,
            'delivery.timeout.ms': 120000,
            # Important for Confluent Cloud stability
            'socket.keepalive.enable': True,
            'max.in.flight.requests.per.connection': 5,
        }
        
        # Add SASL configuration if needed
        if security_protocol == "SASL_SSL":
            config['security.protocol'] = 'SASL_SSL'
            config['sasl.mechanism'] = sasl_mechanism or 'PLAIN'
            config['sasl.username'] = sasl_plain_username
            config['sasl.password'] = sasl_plain_password
        
        self.producer = Producer(config)
        logger.info(f"Kafka producer initialized: {bootstrap_servers}")

    def _delivery_callback(self, err, msg):
        """Callback for message delivery reports"""
        if err:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.debug(
                f'Message delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}'
            )

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

            # Serialize value to JSON bytes
            value_bytes = json.dumps(value).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None
            
            # Convert headers to list of tuples
            kafka_headers = None
            if headers:
                kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]

            # Send message
            self.producer.produce(
                topic=topic,
                value=value_bytes,
                key=key_bytes,
                partition=partition if partition is not None else -1,
                headers=kafka_headers,
                callback=callback or self._delivery_callback,
            )
            
            # Poll to handle delivery callbacks
            self.producer.poll(0)

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
        for i, msg in enumerate(messages):
            key = keys[i] if keys and i < len(keys) else None
            self.send(topic, msg, key=key)
        
        # Flush to ensure all messages are sent
        self.flush()
        return []

    def flush(self, timeout: Optional[int] = None):
        """Flush pending messages"""
        remaining = self.producer.flush(timeout=timeout or 30)
        if remaining > 0:
            logger.warning(f'{remaining} messages were not delivered')

    def close(self):
        """Close the producer"""
        self.flush()
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


# TODO: Add automatic retry logic
# TODO: Add message delivery confirmation
# TODO: Add metrics for monitoring
# TODO: Add support for Avro/Protobuf serialization
