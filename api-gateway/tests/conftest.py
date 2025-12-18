import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime
import sys
import os

# Set up environment variables before importing app
# Use direct assignment to ensure test values are used
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['KAFKA_BOOTSTRAP_SERVERS'] = 'localhost:9092'
os.environ['POSTGRES_PASSWORD'] = 'test-password-for-testing'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from proto import analytics_pb2, ingestion_pb2, common_pb2
from services.websocket_manager import ConnectionManager

@pytest.fixture
def client():
    """Test client with properly initialized app state"""
    # Initialize WebSocket manager for tests
    if not hasattr(app.state, 'ws_manager'):
        app.state.ws_manager = ConnectionManager.get_instance()
    
    # Mock the Kafka consumer to prevent connection attempts during tests
    if not hasattr(app.state, 'kafka_consumer'):
        mock_kafka_consumer = MagicMock()
        mock_kafka_consumer.start = AsyncMock()
        mock_kafka_consumer.stop = AsyncMock()
        app.state.kafka_consumer = mock_kafka_consumer
    
    return TestClient(app)

@pytest.fixture
def mock_analytics_stub(mocker):
    stub = MagicMock()
    mocker.patch('api.analytics.get_analytics_stub', return_value=stub)
    return stub

@pytest.fixture
def mock_ingestion_stub(mocker):
    stub = MagicMock()
    mocker.patch('api.ingestion.get_ingestion_stub', return_value=stub)
    return stub
