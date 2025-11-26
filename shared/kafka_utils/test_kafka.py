#!/usr/bin/env python3
"""Test Kafka utilities"""

import sys
import time

from .consumer import KafkaConsumerWrapper, MarketDataConsumer
from .producer import KafkaProducerWrapper, MarketDataProducer


def test_producer_consumer():
    """Test Kafka producer and consumer"""
    bootstrap_servers = "localhost:9092"
    test_topic = "test-topic"

    # Create producer
    producer_wrapper = KafkaProducerWrapper(
        bootstrap_servers=bootstrap_servers, client_id="test-producer"
    )
    print("✓ Producer created")

    # Send test messages
    for i in range(5):
        message = {"id": i, "message": f"Test message {i}", "tenant_id": "test-tenant"}
        future = producer_wrapper.send(test_topic, message, key=f"key-{i}")
        future.get(timeout=10)  # Wait for confirmation

    producer_wrapper.flush()
    print("✓ Sent 5 test messages")

    # Create consumer
    messages_received = []

    def handler(message):
        messages_received.append(message)
        print(f"✓ Received: {message}")

    consumer_wrapper = KafkaConsumerWrapper(
        topics=[test_topic],
        bootstrap_servers=bootstrap_servers,
        group_id="test-consumer-group",
        auto_offset_reset="earliest",
    )
    print("✓ Consumer created")

    # Consume messages
    consumer_wrapper.consume(handler, max_messages=5, timeout_ms=5000)

    # Verify
    assert len(messages_received) == 5
    print("✓ Received all 5 messages")

    # Cleanup
    producer_wrapper.close()
    consumer_wrapper.close()
    print("✓ Cleanup complete")


def test_market_data_producer():
    """Test specialized market data producer"""
    bootstrap_servers = "localhost:9092"
    topic = "crypto.raw.market-data"

    producer_wrapper = KafkaProducerWrapper(
        bootstrap_servers=bootstrap_servers, client_id="test-market-producer"
    )

    market_producer = MarketDataProducer(producer_wrapper, topic)

    # Publish market data
    future = market_producer.publish_market_data(
        tenant_id="test-tenant",
        symbol="BTCUSDT",
        price=45000.50,
        volume=1.25,
        timestamp=int(time.time() * 1000),
        metadata={"test": True},
    )

    future.get(timeout=10)
    print("✓ Published market data message")

    producer_wrapper.close()


if __name__ == "__main__":
    print("Testing Kafka Producer/Consumer...")
    test_producer_consumer()
    print("\nTesting Market Data Producer...")
    test_market_data_producer()
    print("\n✓ All Kafka tests passed!")
