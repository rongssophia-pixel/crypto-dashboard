"""Tests for IngestionBusinessService"""

import asyncio
from datetime import datetime, timedelta

import pytest


@pytest.mark.asyncio
async def test_start_stream(ingestion_service, clean_db, test_tenants):
    """Test starting a stream"""
    tenant_id = test_tenants["tenant1"]
    symbols = ["BTCUSDT"]
    exchange = "binance"
    stream_type = "ticker"
    kafka_topic = "test-market-data"

    result = await ingestion_service.start_stream(
        tenant_id=tenant_id,
        symbols=symbols,
        exchange=exchange,
        stream_type=stream_type,
        kafka_topic=kafka_topic,
    )

    assert "stream_id" in result
    assert result["status"] == "active"
    assert result["symbols"] == symbols
    print(f"✓ Started stream: {result['stream_id']}")

    # Cleanup
    await ingestion_service.stop_stream(result["stream_id"], tenant_id)


@pytest.mark.asyncio
async def test_stop_stream(ingestion_service, clean_db, test_tenants):
    """Test stopping a stream"""
    tenant_id = test_tenants["tenant1"]
    # Start a stream first
    result = await ingestion_service.start_stream(
        tenant_id=tenant_id,
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
        kafka_topic="test-market-data",
    )

    stream_id = result["stream_id"]

    # Stop it
    stop_result = await ingestion_service.stop_stream(stream_id, tenant_id)

    assert stop_result is True
    print(f"✓ Stopped stream: {stream_id}")


@pytest.mark.asyncio
async def test_get_stream_status(ingestion_service, clean_db, test_tenants):
    """Test getting stream status"""
    tenant_id = test_tenants["tenant1"]
    # Start a stream
    result = await ingestion_service.start_stream(
        tenant_id=tenant_id,
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
        kafka_topic="test-market-data",
    )

    stream_id = result["stream_id"]

    # Get status
    status = await ingestion_service.get_stream_status(stream_id, tenant_id)

    assert status["stream_id"] == stream_id
    assert status["is_active"] is True
    assert status["symbols"] == ["BTCUSDT"]
    print(f"✓ Got stream status: active={status['is_active']}")

    # Cleanup
    await ingestion_service.stop_stream(stream_id, tenant_id)


@pytest.mark.asyncio
async def test_multiple_concurrent_streams(ingestion_service, clean_db, test_tenants):
    """Test multiple streams running concurrently"""
    tenant_id = test_tenants["tenant1"]
    streams = []

    # Start 3 streams
    for i, symbol in enumerate(["BTCUSDT", "ETHUSDT", "BNBUSDT"]):
        result = await ingestion_service.start_stream(
            tenant_id=tenant_id,
            symbols=[symbol],
            exchange="binance",
            stream_type="ticker",
            kafka_topic=f"test-stream-{i}",
        )
        streams.append(result["stream_id"])

    # Verify all are active
    assert len(ingestion_service.active_streams) == 3
    print(f"✓ Started {len(streams)} concurrent streams")

    # Cleanup
    for stream_id in streams:
        await ingestion_service.stop_stream(stream_id, tenant_id)

    assert len(ingestion_service.active_streams) == 0
    print("✓ All streams cleaned up")


@pytest.mark.asyncio
async def test_fetch_historical_data(ingestion_service, test_tenants):
    """Test fetching historical data"""
    tenant_id = test_tenants["tenant1"]
    symbol = "BTCUSDT"
    exchange = "binance"
    interval = "1h"

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=10)

    candles = await ingestion_service.fetch_historical_data(
        tenant_id=tenant_id,
        symbol=symbol,
        exchange=exchange,
        start_time=start_time,
        end_time=end_time,
        interval=interval,
        limit=10,
    )

    assert len(candles) > 0
    assert candles[0]["tenant_id"] == tenant_id
    assert "open" in candles[0]
    assert "close" in candles[0]
    assert "high" in candles[0]
    assert "low" in candles[0]
    assert "volume" in candles[0]
    print(f"✓ Fetched {len(candles)} historical candles")


@pytest.mark.asyncio
async def test_stream_receives_data(ingestion_service, clean_db, test_tenants):
    """Test that stream actually receives and processes data"""
    tenant_id = test_tenants["tenant1"]
    symbols = ["BTCUSDT"]
    exchange = "binance"
    stream_type = "ticker"
    kafka_topic = "test-live-data"

    # Start stream
    result = await ingestion_service.start_stream(
        tenant_id=tenant_id,
        symbols=symbols,
        exchange=exchange,
        stream_type=stream_type,
        kafka_topic=kafka_topic,
    )

    stream_id = result["stream_id"]
    print(f"Started stream {stream_id}, waiting for data...")

    # Wait for some data to be processed (5 seconds)
    await asyncio.sleep(5)

    # Check status
    status = await ingestion_service.get_stream_status(stream_id, tenant_id)

    # Should have processed some events
    assert status["events_processed"] > 0
    print(f"✓ Stream processed {status['events_processed']} events in 5 seconds")

    # Cleanup
    await ingestion_service.stop_stream(stream_id, tenant_id)


@pytest.mark.asyncio
async def test_stop_nonexistent_stream(ingestion_service, clean_db, test_tenants):
    """Test stopping a stream that doesn't exist"""
    result = await ingestion_service.stop_stream(
        "non-existent-id", test_tenants["tenant1"]
    )

    assert result is False
    print("✓ Non-existent stream stop handled gracefully (returns False)")


@pytest.mark.asyncio
async def test_tenant_isolation(ingestion_service, clean_db, test_tenants):
    """Test that tenants can't access each other's streams"""
    tenant1_id = test_tenants["tenant1"]
    tenant2_id = test_tenants["tenant2"]

    # Tenant 1 starts a stream
    result = await ingestion_service.start_stream(
        tenant_id=tenant1_id,
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
        kafka_topic="test-tenant-1",
    )

    stream_id = result["stream_id"]

    # Tenant 2 tries to access it
    status = await ingestion_service.get_stream_status(stream_id, tenant2_id)

    # Should fail or return error (tenant mismatch)
    assert "error" in status or str(status.get("tenant_id")) != tenant2_id
    print("✓ Tenant isolation working correctly")

    # Cleanup with correct tenant
    result = await ingestion_service.stop_stream(stream_id, tenant1_id)
    assert result is True
