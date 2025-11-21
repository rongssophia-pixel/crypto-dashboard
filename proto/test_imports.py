#!/usr/bin/env python3
"""
Test script to verify that all proto files are generated correctly
and can be imported without errors.

Run this after generating proto files:
    python proto/test_imports.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_common_proto():
    """Test common proto imports."""
    print("Testing common.proto...")
    try:
        from proto import common_pb2

        # Test creating common messages
        timestamp = common_pb2.Timestamp(seconds=1234567890, nanos=123456789)
        tenant_context = common_pb2.TenantContext(
            tenant_id="test-tenant", user_id="test-user", roles=["admin"]
        )
        status = common_pb2.Status(success=True, message="OK", code=200)
        _ = common_pb2.Empty()  # noqa: F841

        print("  ✓ common_pb2 imported successfully")
        print("  ✓ Created Timestamp: {}s".format(timestamp.seconds))
        print(f"  ✓ Created TenantContext: tenant={tenant_context.tenant_id}")
        print(f"  ✓ Created Status: {status.message}")
        print("  ✓ Created Empty message")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_ingestion_proto():
    """Test ingestion proto imports."""
    print("\nTesting ingestion.proto...")
    try:
        from proto import ingestion_pb2, ingestion_pb2_grpc

        # Test creating ingestion messages
        request = ingestion_pb2.StartStreamRequest()
        request.context.tenant_id = "test-tenant"
        request.symbols.append("BTCUSDT")
        request.exchange = "binance"
        request.stream_type = "ticker"

        print("  ✓ ingestion_pb2 imported successfully")
        print("  ✓ ingestion_pb2_grpc imported successfully")
        print(f"  ✓ Created StartStreamRequest: {list(request.symbols)}")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_analytics_proto():
    """Test analytics proto imports."""
    print("\nTesting analytics.proto...")
    try:
        from proto import analytics_pb2, analytics_pb2_grpc

        # Test creating analytics messages
        query = analytics_pb2.QueryRequest()
        query.context.tenant_id = "test-tenant"
        query.symbols.append("BTCUSDT")
        query.limit = 100
        query.order_by = "timestamp_desc"

        print("  ✓ analytics_pb2 imported successfully")
        print("  ✓ analytics_pb2_grpc imported successfully")
        print(f"  ✓ Created QueryRequest: {list(query.symbols)}")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_storage_proto():
    """Test storage proto imports."""
    print("\nTesting storage.proto...")
    try:
        from proto import storage_pb2, storage_pb2_grpc

        # Test creating storage messages
        request = storage_pb2.ArchiveRequest()
        request.context.tenant_id = "test-tenant"
        request.symbols.append("BTCUSDT")
        request.data_type = "market_data"

        print("  ✓ storage_pb2 imported successfully")
        print("  ✓ storage_pb2_grpc imported successfully")
        print(f"  ✓ Created ArchiveRequest: data_type={request.data_type}")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_notification_proto():
    """Test notification proto imports."""
    print("\nTesting notification.proto...")
    try:
        from proto import notification_pb2, notification_pb2_grpc

        # Test creating notification messages
        request = notification_pb2.NotificationRequest()
        request.context.tenant_id = "test-tenant"
        request.user_id = "user-123"
        request.type = notification_pb2.EMAIL
        request.subject = "Test Notification"
        request.body = "This is a test message"
        request.recipients.append("test@example.com")
        request.priority = notification_pb2.NORMAL

        print("  ✓ notification_pb2 imported successfully")
        print("  ✓ notification_pb2_grpc imported successfully")
        print(f"  ✓ Created NotificationRequest: {request.subject}")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all proto import tests."""
    print("=" * 60)
    print("Proto Import Test Suite")
    print("=" * 60)

    results = []

    # Run all tests
    results.append(("common.proto", test_common_proto()))
    results.append(("ingestion.proto", test_ingestion_proto()))
    results.append(("analytics.proto", test_analytics_proto()))
    results.append(("storage.proto", test_storage_proto()))
    results.append(("notification.proto", test_notification_proto()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n✓ All proto imports working correctly!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please check proto generation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
