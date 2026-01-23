"""
Quick test script for auto-ingestion functionality
Run with: python test_auto_ingestion.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from connectors.binance_connector import BinanceConnector
from config import settings


async def test_fetch_symbols():
    """Test fetching all USDT trading symbols"""
    print("=" * 60)
    print("TEST: Fetching USDT trading symbols")
    print("=" * 60)
    
    connector = BinanceConnector(
        websocket_url=settings.binance_websocket_url
    )
    connector.rest_base_url = settings.binance_rest_api_url
    
    symbols = await connector.get_all_trading_symbols(quote_currency="USDT")
    
    print(f"✅ Found {len(symbols)} USDT trading pairs")
    print(f"First 10 symbols: {symbols[:10]}")
    print()
    
    return len(symbols) > 0


async def test_kline_stream():
    """Test kline stream for a single symbol"""
    print("=" * 60)
    print("TEST: Kline stream (5 seconds)")
    print("=" * 60)
    
    message_count = 0
    
    def kline_callback(data):
        nonlocal message_count
        message_count += 1
        if message_count <= 3:
            print(f"Received kline message #{message_count}")
            print(f"  Stream: {data.get('stream', 'N/A')}")
            if 'data' in data and 'k' in data['data']:
                kline = data['data']['k']
                print(f"  Symbol: {kline.get('s')}")
                print(f"  Interval: {kline.get('i')}")
                print(f"  Close: {kline.get('c')}")
    
    connector = BinanceConnector(
        websocket_url=settings.binance_websocket_url
    )
    
    # Test with just BTC
    connection_ids = await connector.start_all_streams(
        symbols=["BTCUSDT"],
        intervals=["1m"],
        kline_callback=kline_callback,
        ticker_callback=None,
        max_symbols_per_connection=1,
    )
    
    print(f"Started {len(connection_ids)} connection(s)")
    
    # Wait for some messages
    await asyncio.sleep(5)
    
    # Stop
    for conn_id in connection_ids:
        await connector.stop_stream(conn_id)
    
    print(f"✅ Received {message_count} messages in 5 seconds")
    print()
    
    return message_count > 0


async def test_ticker_stream():
    """Test ticker stream for a single symbol"""
    print("=" * 60)
    print("TEST: Ticker stream (5 seconds)")
    print("=" * 60)
    
    message_count = 0
    
    def ticker_callback(data):
        nonlocal message_count
        message_count += 1
        if message_count <= 2:
            print(f"Received ticker message #{message_count}")
            print(f"  Stream: {data.get('stream', 'N/A')}")
            if 'data' in data:
                ticker = data['data']
                print(f"  Symbol: {ticker.get('s')}")
                print(f"  Price: {ticker.get('c')}")
                print(f"  24h Change: {ticker.get('P')}%")
    
    connector = BinanceConnector(
        websocket_url=settings.binance_websocket_url
    )
    
    # Test with just BTC
    connection_ids = await connector.start_all_streams(
        symbols=["BTCUSDT"],
        intervals=["1m"],
        kline_callback=lambda x: None,  # Ignore klines
        ticker_callback=ticker_callback,
        max_symbols_per_connection=1,
    )
    
    print(f"Started {len(connection_ids)} connection(s)")
    
    # Wait for some messages
    await asyncio.sleep(5)
    
    # Stop
    for conn_id in connection_ids:
        await connector.stop_stream(conn_id)
    
    print(f"✅ Received {message_count} messages in 5 seconds")
    print()
    
    return message_count > 0


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AUTO-INGESTION FUNCTIONALITY TESTS")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Fetch symbols
    try:
        result = await test_fetch_symbols()
        results.append(("Fetch USDT symbols", result))
    except Exception as e:
        print(f"❌ Test failed: {e}\n")
        results.append(("Fetch USDT symbols", False))
    
    # Test 2: Kline stream
    try:
        result = await test_kline_stream()
        results.append(("Kline stream", result))
    except Exception as e:
        print(f"❌ Test failed: {e}\n")
        results.append(("Kline stream", False))
    
    # Test 3: Ticker stream
    try:
        result = await test_ticker_stream()
        results.append(("Ticker stream", result))
    except Exception as e:
        print(f"❌ Test failed: {e}\n")
        results.append(("Ticker stream", False))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    print()
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")
    print("=" * 60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)



