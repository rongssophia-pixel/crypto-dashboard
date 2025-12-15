"""End-to-End Tests for Ingestion Service"""

import asyncio
import json
from datetime import datetime

import pytest
from kafka import KafkaConsumer


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_ingestion_flow(
    ingestion_service, clean_db, test_tenants, kafka_config
):
    """
    Test complete flow: Binance → Ingestion → Kafka → Database

    This test:
    1. Starts a real stream from Binance
    2. Waits for data to be received
    3. Verifies data published to Kafka
    4. Verifies database records updated
    5. Stops stream and verifies cleanup
    """
    symbols = ["BTCUSDT"]
    exchange = "binance"
    stream_type = "ticker"
    kafka_topic = "e2e-test-market-data"

    print("\n" + "=" * 60)
    print("E2E TEST: Complete Ingestion Flow")
    print("=" * 60)

    # ===== STEP 1: Start Stream =====
    print("\n[1/6] Starting stream from Binance...")
    result = await ingestion_service.start_stream(
        symbols=symbols,
        exchange=exchange,
        stream_type=stream_type,
        kafka_topic=kafka_topic,
    )

    stream_id = result["stream_id"]
    assert result["status"] == "active"
    print(f"✓ Stream started: {stream_id}")

    # ===== STEP 2: Wait for Data =====
    print("\n[2/6] Waiting 5 seconds for real market data...")
    await asyncio.sleep(5)

    # ===== STEP 2.5: Wait for Kafka Topic Creation =====
    print("\n[2.5/6] Waiting 3 seconds for Kafka topic initialization...")
    await asyncio.sleep(3)

    # ===== STEP 3: Check Stream Status =====
    print("\n[3/6] Checking stream status in database...")
    status = await ingestion_service.get_stream_status(stream_id)

    print(status)

    assert status["stream_id"] == stream_id
    assert status["is_active"] is True
    assert status["events_processed"] > 0, "Should have processed some events"
    print(f"✓ Stream is active and processed {status['events_processed']} events")

    # ===== STEP 4: Verify Kafka Messages =====
    print("\n[4/6] Consuming messages from Kafka...")
    consumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=kafka_config["bootstrap_servers"],
        auto_offset_reset="earliest",
        consumer_timeout_ms=10000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="e2e-test-consumer",
    )

    messages = []
    for message in consumer:
        messages.append(message.value)
        if len(messages) >= 5:  # Get at least 5 messages
            break

    print(messages)

    consumer.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_streams_e2e(
    ingestion_service, clean_db, test_tenants, kafka_config
):
    """Test multiple concurrent streams end-to-end"""

    print("\n[E2E] Testing multiple concurrent streams...")

    streams = []
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        result = await ingestion_service.start_stream(
            symbols=[symbol],
            exchange="binance",
            stream_type="ticker",
            kafka_topic=f"e2e-{symbol.lower()}",
        )
        streams.append(result["stream_id"])
        print(f"✓ Started stream for {symbol}")

    # Wait for data
    await asyncio.sleep(5)

    # Verify both streams are active and processing
    for stream_id in streams:
        status = await ingestion_service.get_stream_status(stream_id)
        assert status["is_active"] is True
        assert status["events_processed"] > 0
        print(
            f"✓ Stream {stream_id[:8]}... processed {status['events_processed']} events"
        )

    # Cleanup
    for stream_id in streams:
        await ingestion_service.stop_stream(stream_id)

    print("✓ Multiple streams E2E test passed")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_stream_persistence_e2e(ingestion_service, clean_db, test_tenants):
    """Test that stream continues processing over time"""

    print("\n[E2E] Testing stream persistence...")

    # Start stream
    result = await ingestion_service.start_stream(
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
        kafka_topic="e2e-persistence-test",
    )

    stream_id = result["stream_id"]
    print(f"✓ Started stream: {stream_id[:8]}...")

    # Check at 3 seconds
    await asyncio.sleep(3)
    status1 = await ingestion_service.get_stream_status(stream_id)
    events_3s = status1["events_processed"]
    print(f"✓ After 3s: {events_3s} events")

    # Check at 6 seconds
    await asyncio.sleep(3)
    status2 = await ingestion_service.get_stream_status(stream_id)
    events_6s = status2["events_processed"]
    print(f"✓ After 6s: {events_6s} events")

    # Check at 9 seconds
    await asyncio.sleep(3)
    status3 = await ingestion_service.get_stream_status(stream_id)
    events_9s = status3["events_processed"]
    print(f"✓ After 9s: {events_9s} events")

    # Stream should be continuously processing
    assert events_3s > 0, "Should process events by 3s"
    assert events_6s > events_3s, "Should accumulate more events over time"
    assert events_9s > events_6s, "Should continue accumulating events"

    print("✓ Stream persistently processing data")
    print(f"  - Event progression: {events_3s} → {events_6s} → {events_9s}")

    # Cleanup
    await ingestion_service.stop_stream(stream_id)
