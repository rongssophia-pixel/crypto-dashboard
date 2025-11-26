#!/usr/bin/env python3
"""Test Binance connector"""

import asyncio
import sys

from .binance_connector import BinanceConnector


async def test_ticker_stream():
    """Test ticker stream"""
    connector = BinanceConnector()

    messages_received = []

    def callback(data):
        messages_received.append(data)
        print(
            f"Ticker: {data['symbol']} - Price: {data['price']}, Volume: {data['volume']}"
        )

    # Start stream
    stream_id = await connector.start_ticker_stream(["BTCUSDT", "ETHUSDT"], callback)
    print(f"Started stream: {stream_id}")

    # Let it run for 10 seconds
    await asyncio.sleep(10)

    # Stop stream
    await connector.stop_stream(stream_id)
    print(f"Stopped stream. Received {len(messages_received)} messages")

    assert len(messages_received) > 0, "Should have received some messages"
    print("✓ Ticker stream test passed")


async def test_historical_data():
    """Test historical data fetch"""
    connector = BinanceConnector()

    candles = await connector.fetch_historical_klines(
        symbol="BTCUSDT", interval="1h", limit=10
    )

    assert len(candles) > 0, "Should have received candles"
    print(f"✓ Fetched {len(candles)} historical candles")

    # Print first candle
    if candles:
        print(f"First candle: {candles[0]}")


async def test_exchange_info():
    """Test exchange info fetch"""
    connector = BinanceConnector()

    info = await connector.get_exchange_info("BTCUSDT")

    assert "symbols" in info or "symbol" in info, "Should have symbol info"
    print("✓ Fetched exchange info")


async def main():
    print("Testing Binance Connector...")
    print("\n1. Testing historical data fetch...")
    await test_historical_data()

    print("\n2. Testing exchange info...")
    await test_exchange_info()

    print("\n3. Testing ticker stream (10 seconds)...")
    await test_ticker_stream()

    print("\n✓ All Binance connector tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
