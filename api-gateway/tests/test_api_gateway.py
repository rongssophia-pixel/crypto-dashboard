import pytest
from datetime import datetime
from proto import analytics_pb2, ingestion_pb2, common_pb2

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "api-gateway"

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_latest_prices(client, mock_analytics_stub):
    # Setup mock
    mock_response = analytics_pb2.QueryResponse()
    point = mock_response.data.add()
    point.symbol = "BTCUSDT"
    point.price = 50000.0
    point.timestamp.seconds = int(datetime.utcnow().timestamp())
    
    mock_analytics_stub.QueryMarketData.return_value = mock_response
    
    response = client.get("/api/v1/analytics/market-data/latest?symbols=BTCUSDT")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["symbol"] == "BTCUSDT"
    assert data[0]["price"] == 50000.0

def test_start_stream(client, mock_ingestion_stub):
    # Setup mock
    mock_response = ingestion_pb2.StartStreamResponse()
    mock_response.stream_id = "stream-123"
    mock_response.success = True
    mock_response.message = "Started"
    
    mock_ingestion_stub.StartDataStream.return_value = mock_response
    
    payload = {
        "symbols": ["BTCUSDT"],
        "exchange": "binance",
        "stream_type": "ticker"
    }
    
    response = client.post("/api/v1/ingestion/streams/start", json=payload)
    assert response.status_code == 200
    assert response.json()["stream_id"] == "stream-123"

def test_stop_stream(client, mock_ingestion_stub):
    # Setup mock (returns Empty, which is None in python usually unless verified)
    mock_ingestion_stub.StopDataStream.return_value = common_pb2.Empty()
    
    response = client.post("/api/v1/ingestion/streams/stream-123/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_get_candles(client, mock_analytics_stub):
    # Setup mock
    mock_response = analytics_pb2.CandleResponse()
    candle = mock_response.candles.add()
    candle.close = 50000.0
    candle.timestamp.seconds = int(datetime.utcnow().timestamp())
    mock_response.total_count = 1
    
    mock_analytics_stub.GetCandles.return_value = mock_response
    
    params = {
        "symbol": "BTCUSDT",
        "start_time": datetime.utcnow().isoformat(),
        "end_time": datetime.utcnow().isoformat()
    }
    
    response = client.get("/api/v1/analytics/candles", params=params)
    assert response.status_code == 200
    assert response.json()["total_count"] == 1
    assert response.json()["candles"][0]["close"] == 50000.0
