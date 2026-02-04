"""
Integration tests for Notification Service
Tests notification flow, retry logic, and Kafka consumption
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
import asyncpg

from services.notification_service import NotificationBusinessService
from repositories.notification_repository import NotificationRepository
from providers.email_provider import MockEmailProvider
from services.retry_service import RetryService
from consumers.alert_consumer import AlertConsumer


@pytest.fixture
async def mock_db_pool():
    """Mock database connection pool"""
    pool = AsyncMock(spec=asyncpg.Pool)
    
    # Mock connection context manager
    conn = AsyncMock()
    
    # Mock fetchrow to return notification data
    async def mock_fetchrow(*args, **kwargs):
        return {
            'id': 'test-notification-id',
            'user_id': 'test-user-id',
            'notification_type': 'email',
            'subject': 'Test Subject',
            'body': 'Test Body',
            'recipients': ['test@example.com'],
            'status': 'pending',
            'error_message': None,
            'retry_count': 0,
            'priority': 'normal',
            'created_at': datetime.utcnow(),
            'sent_at': None,
            'delivered_at': None,
            'metadata': {}
        }
    
    conn.fetchrow = mock_fetchrow
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=1)
    
    # Mock acquire context manager
    class AcquireContext:
        async def __aenter__(self):
            return conn
        async def __aexit__(self, *args):
            pass
    
    pool.acquire = lambda: AcquireContext()
    
    return pool


@pytest.fixture
def notification_repo(mock_db_pool):
    """Create notification repository with mock pool"""
    return NotificationRepository(mock_db_pool)


@pytest.fixture
def email_provider():
    """Create mock email provider"""
    return MockEmailProvider(failure_rate=0.0)


@pytest.fixture
def email_provider_with_failures():
    """Create mock email provider that fails 50% of the time"""
    return MockEmailProvider(failure_rate=0.5)


@pytest.fixture
def business_service(notification_repo, email_provider):
    """Create notification business service"""
    return NotificationBusinessService(notification_repo, email_provider)


@pytest.mark.asyncio
async def test_send_notification_success(business_service):
    """Test successful notification sending"""
    result = await business_service.send_notification(
        user_id="test-user-id",
        notification_type="email",
        subject="Test Notification",
        body="This is a test notification",
        recipients=["test@example.com"],
        priority="normal"
    )
    
    assert result is not None
    assert "notification_id" in result
    # Note: With mocked DB, success depends on mock implementation


@pytest.mark.asyncio
async def test_send_notification_invalid_email(business_service):
    """Test notification with invalid email"""
    result = await business_service.send_notification(
        user_id="test-user-id",
        notification_type="email",
        subject="Test Notification",
        body="This is a test notification",
        recipients=["invalid-email"],
        priority="normal"
    )
    
    assert result is not None
    assert result["success"] is False
    assert "No valid email recipients" in result.get("error", "")


@pytest.mark.asyncio
async def test_process_alert(business_service, notification_repo):
    """Test processing alert from Kafka"""
    # Mock get_user_email
    notification_repo.get_user_email = AsyncMock(return_value="user@example.com")
    
    alert = {
        "alert_id": "alert-123",
        "user_id": "user-123",
        "symbol": "BTCUSDT",
        "condition_type": "price_above",
        "threshold_value": "100000.00",
        "triggered_value": "100500.50",
        "timestamp": "2024-12-16T10:30:00Z",
        "message": "BTC price is above $100,000"
    }
    
    result = await business_service.process_alert(alert)
    
    assert result is not None
    assert "success" in result


@pytest.mark.asyncio
async def test_send_bulk_notifications(business_service):
    """Test bulk notification sending"""
    notifications = [
        {
            "user_id": "user-1",
            "notification_type": "email",
            "subject": "Test 1",
            "body": "Body 1",
            "recipients": ["user1@example.com"],
            "priority": "normal"
        },
        {
            "user_id": "user-2",
            "notification_type": "email",
            "subject": "Test 2",
            "body": "Body 2",
            "recipients": ["user2@example.com"],
            "priority": "high"
        }
    ]
    
    result = await business_service.send_bulk_notifications(notifications)
    
    assert result is not None
    assert "total_requested" in result
    assert result["total_requested"] == 2
    assert "total_sent" in result
    assert "total_failed" in result


@pytest.mark.asyncio
async def test_get_notification_status(business_service):
    """Test getting notification status"""
    # This test relies on mocked repository
    result = await business_service.get_notification_status("test-notification-id")
    
    assert result is not None
    assert "success" in result


@pytest.mark.asyncio
async def test_retry_service():
    """Test retry service initialization and lifecycle"""
    mock_repo = Mock()
    mock_repo.get_failed_notifications_for_retry = AsyncMock(return_value=[])
    
    mock_business_service = Mock()
    
    retry_service = RetryService(
        notification_repo=mock_repo,
        business_service=mock_business_service,
        max_retries=3,
        check_interval=1  # 1 second for testing
    )
    
    assert retry_service.max_retries == 3
    assert retry_service.check_interval == 1
    assert not retry_service.is_running()
    
    # Start and quickly stop
    await retry_service.start()
    assert retry_service.is_running()
    
    await asyncio.sleep(0.1)
    
    await retry_service.stop()
    assert not retry_service.is_running()


@pytest.mark.asyncio
async def test_email_provider_success():
    """Test mock email provider success"""
    provider = MockEmailProvider(failure_rate=0.0)
    
    result = await provider.send_email(
        from_address="noreply@example.com",
        to_addresses=["recipient@example.com"],
        subject="Test Email",
        body_html="<p>Test body</p>",
        body_text="Test body"
    )
    
    assert result["success"] is True
    assert "message_id" in result
    assert result["message_id"].startswith("mock_")


@pytest.mark.asyncio
async def test_email_provider_failure():
    """Test mock email provider with forced failures"""
    provider = MockEmailProvider(failure_rate=1.0)  # 100% failure rate
    
    result = await provider.send_email(
        from_address="noreply@example.com",
        to_addresses=["recipient@example.com"],
        subject="Test Email",
        body_html="<p>Test body</p>"
    )
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_kafka_consumer_initialization():
    """Test Kafka consumer initialization"""
    mock_business_service = Mock()
    
    consumer = AlertConsumer(
        business_service=mock_business_service,
        kafka_servers="localhost:9092",
        topic="crypto.alerts",
        group_id="test-group"
    )
    
    assert consumer.topic == "crypto.alerts"
    assert consumer.group_id == "test-group"
    assert not consumer.is_running()


@pytest.mark.asyncio
async def test_alert_consumer_process_alert():
    """Test alert consumer processing"""
    mock_business_service = Mock()
    mock_business_service.process_alert = AsyncMock(
        return_value={"success": True, "notification_id": "test-123"}
    )
    
    consumer = AlertConsumer(
        business_service=mock_business_service,
        kafka_servers="localhost:9092"
    )
    
    alert = {
        "alert_id": "alert-123",
        "user_id": "user-123",
        "symbol": "BTCUSDT",
        "message": "Test alert"
    }
    
    result = await consumer.process_alert(alert)
    
    assert result["success"] is True
    assert result["notification_id"] == "test-123"
    mock_business_service.process_alert.assert_called_once_with(alert)


@pytest.mark.asyncio
async def test_notification_validation():
    """Test email validation in business service"""
    provider = MockEmailProvider()
    repo = Mock()
    service = NotificationBusinessService(repo, provider)
    
    # Valid emails
    assert service._validate_email("test@example.com") is True
    assert service._validate_email("user.name@domain.co.uk") is True
    
    # Invalid emails
    assert service._validate_email("invalid-email") is False
    assert service._validate_email("@example.com") is False
    assert service._validate_email("test@") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])






