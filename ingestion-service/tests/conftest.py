"""Pytest fixtures for ingestion service tests"""

import os
import sys

import pytest
from psycopg2.pool import SimpleConnectionPool

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shared"))
)

from connectors.binance_connector import BinanceConnector
from kafka_utils.producer import KafkaProducerWrapper
from repositories.kafka_repository import KafkaRepository
from repositories.stream_repository import StreamRepository
from services.ingestion_service import IngestionBusinessService


@pytest.fixture(scope="session")
def db_config():
    """Database configuration for tests"""
    return {
        "host": "localhost",
        "port": 5432,
        "database": "crypto_dashboard",
        "user": "postgres",
        "password": "postgres",
    }


@pytest.fixture(scope="session")
def db_pool(db_config):
    """Create database connection pool for tests"""
    pool = SimpleConnectionPool(minconn=1, maxconn=5, **db_config)
    yield pool
    pool.closeall()


@pytest.fixture(scope="session")
def test_tenants(db_pool):
    """Create test tenant records for testing"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        # Create test tenants with fixed UUIDs
        cursor.execute(
            """
            INSERT INTO tenants (id, name, api_key, is_active) VALUES
                ('11111111-1111-1111-1111-111111111111', 'Test Tenant 1', 'test-key-1', true),
                ('22222222-2222-2222-2222-222222222222', 'Test Tenant 2', 'test-key-2', true)
            ON CONFLICT (api_key) DO NOTHING;
        """
        )
        conn.commit()
        return {
            "tenant1": "11111111-1111-1111-1111-111111111111",
            "tenant2": "22222222-2222-2222-2222-222222222222",
        }
    finally:
        db_pool.putconn(conn)


@pytest.fixture(scope="function")
def clean_db(db_pool, test_tenants):
    """Clean database before each test (but keep test tenants)"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stream_sessions;")
        # Don't delete tenants - they're reused across tests
        conn.commit()
    finally:
        db_pool.putconn(conn)


@pytest.fixture
def stream_repository(db_pool):
    """Create stream repository instance"""
    return StreamRepository(db_pool)


@pytest.fixture
def kafka_config():
    """Kafka configuration for tests"""
    return {
        "bootstrap_servers": "localhost:9092",
        "client_id": "test-ingestion-service",
    }


@pytest.fixture
def kafka_producer(kafka_config):
    """Create Kafka producer for tests"""
    producer = KafkaProducerWrapper(
        bootstrap_servers=kafka_config["bootstrap_servers"],
        client_id=kafka_config["client_id"],
    )
    yield producer
    producer.close()


@pytest.fixture
def kafka_repository(kafka_producer):
    """Create Kafka repository instance"""
    return KafkaRepository(kafka_producer)


@pytest.fixture
def binance_connector():
    """Create Binance connector instance"""
    return BinanceConnector()


@pytest.fixture
def ingestion_service(stream_repository, kafka_repository, binance_connector):
    """Create ingestion business service instance"""
    return IngestionBusinessService(
        stream_repository=stream_repository,
        kafka_repository=kafka_repository,
        binance_connector=binance_connector,
    )
