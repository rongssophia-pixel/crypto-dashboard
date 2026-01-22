#!/usr/bin/env python3
"""
Test script for Binance WebSocket connection
Run this to isolate the connection issue
"""

import asyncio
import json
import websockets
import sys


async def test_binance_websocket():
    """Test WebSocket connection to Binance"""

    # Test both URL formats
    test_urls = [
        "wss://stream.binance.us:9443/ws/btcusdt@ticker",
        "wss://stream.binance.us:9443/stream?streams=btcusdt@ticker",
    ]

    for url in test_urls:
        print(f"\n{'=' * 60}")
        print(f"Testing URL: {url}")
        print(f"{'=' * 60}")

        try:
            print("Attempting to connect...")

            async with websockets.connect(url) as websocket:
                print("✅ Connection successful!")
                print(f"WebSocket state: {websocket.state}")

                # Receive a few messages
                message_count = 0
                async for message in websocket:
                    message_count += 1
                    data = json.loads(message)
                    print(f"\n📨 Message {message_count}:")
                    print(json.dumps(data, indent=2)[:500])

                    if message_count >= 3:
                        print("\n✅ Successfully received 3 messages!")
                        break

        except websockets.exceptions.InvalidStatusCode as e:
            print(f"❌ Connection rejected with HTTP status {e.status_code}")
            print(f"   Error details: {e}")

        except Exception as e:
            print(f"❌ Connection failed: {type(e).__name__}")
            print(f"   Error details: {e}")

        # Small delay between tests
        await asyncio.sleep(1)

    print(f"\n{'=' * 60}")
    print("Test complete")
    print(f"{'=' * 60}")


async def test_with_options():
    """Test with various connection options"""

    url = "wss://stream.binance.us:9443/stream?streams=btcusdt@ticker"

    print(f"\n{'=' * 60}")
    print("Testing with connection options...")
    print(f"URL: {url}")
    print(f"{'=' * 60}")

    try:
        print("\nAttempting connection with explicit options...")

        async with websockets.connect(
                url,
                max_size=2 ** 23,  # 8MB
                compression=None,  # Disable compression
                open_timeout=10,
                close_timeout=10,
                additional_headers={},
        ) as websocket:
            print("✅ Connection successful with options!")

            # Get one message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"\n📨 Received message:")
            print(json.dumps(data, indent=2)[:500])

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection rejected with HTTP status {e.status_code}")
        print(f"   Error details: {e}")

    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}")
        print(f"   Error details: {e}")


async def test_with_headers():
    """Test with custom headers"""

    url = "wss://stream.binance.us:9443/stream?streams=btcusdt@ticker"

    print(f"\n{'=' * 60}")
    print("Testing with custom headers...")
    print(f"URL: {url}")
    print(f"{'=' * 60}")

    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    try:
        print(f"\nAttempting connection with headers: {headers}")

        async with websockets.connect(
                url,
                extra_headers=headers,
        ) as websocket:
            print("✅ Connection successful with headers!")

            # Get one message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"\n📨 Received message:")
            print(json.dumps(data, indent=2)[:500])

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection rejected with HTTP status {e.status_code}")
        print(f"   Error details: {e}")

    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}")
        print(f"   Error details: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Binance WebSocket Connection Test")
    print("=" * 60)

    # Print Python and websockets version
    print(f"\nPython version: {sys.version}")
    print(f"Websockets version: {websockets.__version__}")

    # Test 1: Basic connection
    await test_binance_websocket()

    # Test 2: With options
    await test_with_options()

    # Test 3: With headers
    await test_with_headers()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()