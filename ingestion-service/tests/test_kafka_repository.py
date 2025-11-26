"""Tests for KafkaRepository"""

import json
import time

import pytest
from kafka import KafkaConsumer


@pytest.mark.asyncio
async def test_publish_market_data(kafka_repository, kafka_config):
    """Test publishing market data to Kafka"""
    tenant_id = "test-tenant-1"
    symbol = "BTCUSDT"
    exchange = "binance"
    topic = "test-market-data"

    data = {
        "price": 50000.0,
        "volume": 1.5,
        "timestamp": int(time.time() * 1000),
    }

    # Publish
    success = await kafka_repository.publish_market_data(
        tenant_id=tenant_id, symbol=symbol, exchange=exchange, data=data, topic=topic
    )

    assert success is True
    print(f"✓ Published market data to {topic}")

    # Verify by consuming
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=kafka_config["bootstrap_servers"],
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    messages = list(consumer)
    consumer.close()

    assert len(messages) > 0
    msg = messages[-1].value
    assert msg["tenant_id"] == tenant_id
    assert msg["symbol"] == symbol
    assert msg["price"] == 50000.0
    print(f"✓ Verified message in Kafka: {msg['symbol']} @ ${msg['price']}")


@pytest.mark.asyncio
async def test_publish_batch(kafka_repository):
    """Test publishing batch of messages"""
    topic = "test-batch-data"

    messages = [
        {"symbol": "BTCUSDT", "price": 50000.0},
        {"symbol": "ETHUSDT", "price": 3000.0},
        {"symbol": "BNBUSDT", "price": 400.0},
    ]

    success_count = await kafka_repository.publish_batch(messages, topic)

    assert success_count == 3
    print(f"✓ Published batch of {success_count} messages")


@pytest.mark.asyncio
async def test_publish_with_enrichment(kafka_repository, kafka_config):
    """Test that data is enriched with tenant context"""
    tenant_id = "test-tenant-1"
    symbol = "ETHUSDT"
    exchange = "binance"
    topic = "test-enriched-data"

    # Minimal data
    data = {"price": 3000.0}

    # Publish
    await kafka_repository.publish_market_data(
        tenant_id=tenant_id, symbol=symbol, exchange=exchange, data=data, topic=topic
    )

    # Verify enrichment
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=kafka_config["bootstrap_servers"],
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    messages = list(consumer)
    consumer.close()

    assert len(messages) > 0
    msg = messages[-1].value

    # Check that all fields are present
    assert msg["tenant_id"] == tenant_id
    assert msg["symbol"] == symbol
    assert msg["exchange"] == exchange
    assert msg["price"] == 3000.0
    print("✓ Data properly enriched with tenant context")


@pytest.mark.asyncio
async def test_publish_handles_errors_gracefully(kafka_repository):
    """Test that publish handles errors gracefully"""
    # Try to publish to an invalid topic or with bad data
    result = await kafka_repository.publish_market_data(
        tenant_id="test",
        symbol="TEST",
        exchange="test",
        data={"price": "invalid"},  # Invalid data type
        topic="test-error-handling",
    )

    # Should not crash, but may return False
    assert isinstance(result, bool)
    print("✓ Error handling works gracefully")
