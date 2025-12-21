#!/usr/bin/env python3
"""
Simple WebSocket test client
Tests WebSocket connection, authentication, and subscriptions
"""

import asyncio
import json
import websockets


async def test_websocket():
    """Test WebSocket connection and subscriptions"""
    uri = "ws://localhost:8000/ws/market-data?token=dev"
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected successfully")
            
            # Receive welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"✓ Welcome message: {welcome_data}")
            
            # Test 1: Subscribe to symbols
            print("\n--- Test 1: Subscribe to symbols ---")
            subscribe_msg = {
                "action": "subscribe",
                "symbols": ["BTCUSDT", "ETHUSDT"]
            }
            await websocket.send(json.dumps(subscribe_msg))
            print(f"Sent: {subscribe_msg}")
            
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"Received: {response_data}")
            assert response_data["type"] == "subscribed"
            print("✓ Subscription confirmed")
            
            # Test 2: List subscriptions
            print("\n--- Test 2: List subscriptions ---")
            list_msg = {"action": "list_subscriptions"}
            await websocket.send(json.dumps(list_msg))
            print(f"Sent: {list_msg}")
            
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"Received: {response_data}")
            assert response_data["type"] == "subscriptions"
            print("✓ Subscriptions listed")
            
            # Test 3: Ping/Pong
            print("\n--- Test 3: Ping/Pong ---")
            ping_msg = {"action": "ping"}
            await websocket.send(json.dumps(ping_msg))
            print(f"Sent: {ping_msg}")
            
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"Received: {response_data}")
            assert response_data["type"] == "pong"
            print("✓ Ping/Pong working")
            
            # Test 4: Wait for market data (if stream processing is running)
            print("\n--- Test 4: Wait for market data ---")
            print("Waiting 10 seconds for market data messages...")
            print("(This requires stream-processing-service to be running)")
            
            try:
                for i in range(10):
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "market_data":
                        print(f"✓ Market data received: {response_data['symbol']} - ${response_data.get('price')}")
                        break
                else:
                    print("⚠ No market data received (stream may not be active)")
                    
            except asyncio.TimeoutError:
                print("⚠ No messages received (stream may not be active)")
            
            # Test 5: Unsubscribe
            print("\n--- Test 5: Unsubscribe ---")
            unsubscribe_msg = {
                "action": "unsubscribe",
                "symbols": ["BTCUSDT"]
            }
            await websocket.send(json.dumps(unsubscribe_msg))
            print(f"Sent: {unsubscribe_msg}")
            
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"Received: {response_data}")
            assert response_data["type"] == "unsubscribed"
            print("✓ Unsubscription confirmed")
            
            print("\n✓ All tests passed!")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"✗ Connection failed: {e}")
        print("Make sure the API Gateway is running on port 8000")
    except ConnectionRefusedError:
        print("✗ Connection refused")
        print("Make sure the API Gateway is running on port 8000")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Test Client")
    print("=" * 60)
    asyncio.run(test_websocket())
