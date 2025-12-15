import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from proto import analytics_pb2, ingestion_pb2, common_pb2

@pytest.fixture
def client():
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
