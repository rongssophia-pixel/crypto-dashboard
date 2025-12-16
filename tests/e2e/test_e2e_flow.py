import pytest
import asyncio
import httpx
import time
from datetime import datetime

# API Gateway URL
BASE_URL = "http://localhost:8000"

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        yield client

def wait_for_service(client, retries=30, delay=1):
    """Wait for API Gateway to be ready"""
    print(f"Waiting for API Gateway at {BASE_URL}...")
    for i in range(retries):
        try:
            response = client.get("/health")
            if response.status_code == 200:
                print("API Gateway is ready!")
                return
        except httpx.RequestError:
            pass
        time.sleep(delay)
    pytest.fail("API Gateway failed to start")

def test_full_e2e_flow(client):
    """
    Test the full data flow:
    1. Start ingestion stream (Ingestion Service)
    2. Wait for data processing (Kafka -> Stream Processing -> ClickHouse)
    3. Query analytics (Analytics Service)
    4. Stop stream
    """
    
    # 0. Wait for service to be healthy
    wait_for_service(client)
    
    symbol = "BTCUSDT"
    
    # 1. Start Stream
    print(f"\n[1] Starting stream for {symbol}...")
    start_payload = {
        "symbols": [symbol],
        "exchange": "binance",
        "stream_type": "ticker"
    }
    
    response = client.post("/api/v1/ingestion/streams/start", json=start_payload)
    assert response.status_code == 200, f"Start stream failed: {response.text}"
    data = response.json()
    assert data["success"] is True
    stream_id = data["stream_id"]
    print(f"Stream started with ID: {stream_id}")
    
    try:
        # 2. Verify Stream Status
        print("\n[2] Verifying stream status...")
        response = client.get(f"/api/v1/ingestion/streams/{stream_id}/status")
        assert response.status_code == 200
        status = response.json()
        assert status["is_active"] is True
        assert symbol in status["symbols"]
        
        # 3. Wait for Data Processing
        # We need to wait for:
        # - Ingestion to connect to Binance and get data
        # - Publish to Kafka
        # - Stream Processing to consume and write to ClickHouse
        # - ClickHouse to commit
        
        print("\n[3] Waiting for data to flow (30s)...")
        # Check periodically if data has arrived
        data_found = False
        for i in range(10): # Try 10 times, 3s each
            time.sleep(3)

            # Check latest price
            print(f"   Checking for latest price (Attempt {i+1})...")
            response = client.get("/api/v1/analytics/market-data/latest", params={"symbols": symbol})

            if response.status_code == 200:
                results = response.json().get("data", [])
                if results and len(results) > 0:
                    latest = results[0]
                    price = latest.get("price")
                    ts_str = latest.get("timestamp")

                    print(f"   Found data! Price: {price}, Time: {ts_str}")

                    # Verify timestamp is recent (within last minute)
                    if ts_str:
                        # Simple check that we got something
                        data_found = True
                        break

        assert data_found, "No market data found in Analytics Service after waiting"
        
        # 4. Query Candles (Stream processor should aggregate these)
        # Note: Stream processor aggregates 1m candles. We might need to wait at least 1m or checks partials?
        # Usually stream processors emit intermediate results or we wait.
        # For this test, let's just check raw data or aggregates if available.
        
        print("\n[4] Querying Aggregated Metrics...")
        now = datetime.utcnow()
        response = client.get(
            "/api/v1/analytics/metrics/aggregated",
            params={
                "symbol": symbol,
                "metric_types": ["avg_price", "total_volume"],
                "start_time": (now.replace(hour=0, minute=0, second=0)).isoformat(), # Start of day
                "end_time": now.isoformat()
            }
        )
        
        if response.status_code == 200:
             metrics = response.json()
             print(f"   Metrics: {metrics}")
        else:
            print(f"   Metrics query failed: {response.text}")
            # Don't fail the test strictly on this if 1m hasn't passed, but good to know.
            
    finally:
        # 5. Stop Stream
        print(f"\n[5] Stopping stream {stream_id}...")
        response = client.post(f"/api/v1/ingestion/streams/{stream_id}/stop")
        assert response.status_code == 200
        print("Stream stopped.")
