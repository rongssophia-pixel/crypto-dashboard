"""Tests for StreamRepository"""

import uuid

import pytest


@pytest.mark.asyncio
async def test_create_stream(stream_repository, clean_db):
    """Test creating a stream session"""
    tenant_id = "test-tenant-1"
    stream_id = str(uuid.uuid4())
    symbols = ["BTCUSDT", "ETHUSDT"]
    exchange = "binance"
    stream_type = "ticker"

    result = await stream_repository.create_stream(
        tenant_id=tenant_id,
        stream_id=stream_id,
        symbols=symbols,
        exchange=exchange,
        stream_type=stream_type,
    )

    assert result is not None
    assert result["stream_id"] == stream_id
    assert result["tenant_id"] == tenant_id
    assert result["symbols"] == symbols
    assert result["status"] == "active"
    assert result["events_processed"] == 0
    print(f"✓ Created stream session: {stream_id}")


@pytest.mark.asyncio
async def test_get_stream(stream_repository, clean_db):
    """Test retrieving a stream session"""
    # Create a stream first
    tenant_id = "test-tenant-1"
    stream_id = str(uuid.uuid4())

    await stream_repository.create_stream(
        tenant_id=tenant_id,
        stream_id=stream_id,
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
    )

    # Retrieve it
    result = await stream_repository.get_stream(stream_id)

    assert result is not None
    assert result["stream_id"] == stream_id
    print(f"✓ Retrieved stream: {stream_id}")


@pytest.mark.asyncio
async def test_increment_event_count(stream_repository, clean_db):
    """Test incrementing event count"""
    stream_id = str(uuid.uuid4())

    await stream_repository.create_stream(
        tenant_id="test-tenant-1",
        stream_id=stream_id,
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
    )

    # Increment 5 times
    for _ in range(5):
        await stream_repository.increment_event_count(stream_id)

    # Check count
    stream = await stream_repository.get_stream(stream_id)
    assert stream["events_processed"] == 5
    print(f"✓ Event count incremented to {stream['events_processed']}")


@pytest.mark.asyncio
async def test_stop_stream(stream_repository, clean_db):
    """Test stopping a stream"""
    stream_id = str(uuid.uuid4())

    await stream_repository.create_stream(
        tenant_id="test-tenant-1",
        stream_id=stream_id,
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
    )

    # Stop the stream
    result = await stream_repository.stop_stream(stream_id)
    assert result is True

    # Verify status
    stream = await stream_repository.get_stream(stream_id)
    assert stream["status"] == "stopped"
    assert stream["stopped_at"] is not None
    print(f"✓ Stream stopped: {stream_id}")


@pytest.mark.asyncio
async def test_list_active_streams_by_tenant(stream_repository, clean_db):
    """Test listing active streams for a tenant"""
    tenant_id = "test-tenant-1"

    # Create 3 streams for this tenant
    for i in range(3):
        await stream_repository.create_stream(
            tenant_id=tenant_id,
            stream_id=str(uuid.uuid4()),
            symbols=[f"SYM{i}USDT"],
            exchange="binance",
            stream_type="ticker",
        )

    # Create 1 stream for another tenant
    await stream_repository.create_stream(
        tenant_id="test-tenant-2",
        stream_id=str(uuid.uuid4()),
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
    )

    # List active streams for tenant-1
    streams = await stream_repository.list_active_streams(tenant_id)
    assert len(streams) == 3
    print(f"✓ Listed {len(streams)} active streams for {tenant_id}")


@pytest.mark.asyncio
async def test_get_nonexistent_stream(stream_repository, clean_db):
    """Test retrieving a non-existent stream"""
    result = await stream_repository.get_stream("non-existent-id")
    assert result is None
    print("✓ Non-existent stream returns None")


@pytest.mark.asyncio
async def test_duplicate_stream_id_fails(stream_repository, clean_db):
    """Test that creating a stream with duplicate ID fails"""
    stream_id = str(uuid.uuid4())

    # Create first stream
    await stream_repository.create_stream(
        tenant_id="test-tenant-1",
        stream_id=stream_id,
        symbols=["BTCUSDT"],
        exchange="binance",
        stream_type="ticker",
    )

    # Try to create duplicate
    with pytest.raises(Exception):
        await stream_repository.create_stream(
            tenant_id="test-tenant-1",
            stream_id=stream_id,  # Same ID
            symbols=["ETHUSDT"],
            exchange="binance",
            stream_type="ticker",
        )
    print("✓ Duplicate stream ID properly rejected")
