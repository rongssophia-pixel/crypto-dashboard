# Ingestion Service Tests

Comprehensive test suite for TICKET-007 implementation.

## Test Files

- **`conftest.py`** - Pytest fixtures and shared test configuration
- **`setup_test_db.sql`** - PostgreSQL schema for test database
- **`test_stream_repository.py`** - Tests for StreamRepository (PostgreSQL operations)
- **`test_kafka_repository.py`** - Tests for KafkaRepository (Kafka publishing)
- **`test_ingestion_service.py`** - Tests for IngestionBusinessService (business logic)

## Prerequisites

### 1. Start Infrastructure

```bash
cd /Users/yuyu/workspace/crypto-dashboard
docker compose up -d postgres kafka
```

### 2. Create Test Database

```bash
# Create database
docker exec -i crypto-postgres psql -U postgres -c "CREATE DATABASE crypto_dashboard;"

# Apply schema
docker exec -i crypto-postgres psql -U postgres -d crypto_dashboard < ingestion-service/tests/setup_test_db.sql
```

### 3. Install Test Dependencies

```bash
cd /Users/yuyu/workspace/crypto-dashboard
source ingestion-service/venv/bin/activate
pip install pytest pytest-asyncio
```

## Running Tests

### Run All Tests

```bash
cd /Users/yuyu/workspace/crypto-dashboard
source ingestion-service/venv/bin/activate
python -m pytest ingestion-service/tests/ -v
```

### Run Specific Test File

```bash
# Stream Repository tests
python -m pytest ingestion-service/tests/test_stream_repository.py -v

# Kafka Repository tests
python -m pytest ingestion-service/tests/test_kafka_repository.py -v

# Business Service tests
python -m pytest ingestion-service/tests/test_ingestion_service.py -v
```

### Run Specific Test

```bash
python -m pytest ingestion-service/tests/test_stream_repository.py::test_create_stream -v
```

### Run with Output (see print statements)

```bash
python -m pytest ingestion-service/tests/ -v -s
```

### Run with Coverage

```bash
pip install pytest-cov
python -m pytest ingestion-service/tests/ --cov=ingestion-service --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Test Coverage

### StreamRepository Tests (7 tests)
- ✅ Create stream session
- ✅ Get stream by ID
- ✅ Increment event count
- ✅ Stop stream
- ✅ List active streams by tenant
- ✅ Get non-existent stream
- ✅ Duplicate stream ID validation

### KafkaRepository Tests (4 tests)
- ✅ Publish single market data message
- ✅ Publish batch of messages
- ✅ Data enrichment with tenant context
- ✅ Error handling

### IngestionBusinessService Tests (8 tests)
- ✅ Start stream
- ✅ Stop stream
- ✅ Get stream status
- ✅ Multiple concurrent streams
- ✅ Fetch historical data
- ✅ Stream receives and processes data
- ✅ Stop non-existent stream
- ✅ Tenant isolation

## Expected Test Results

```
test_stream_repository.py::test_create_stream PASSED
test_stream_repository.py::test_get_stream PASSED
test_stream_repository.py::test_increment_event_count PASSED
test_stream_repository.py::test_stop_stream PASSED
test_stream_repository.py::test_list_active_streams_by_tenant PASSED
test_stream_repository.py::test_get_nonexistent_stream PASSED
test_stream_repository.py::test_duplicate_stream_id_fails PASSED

test_kafka_repository.py::test_publish_market_data PASSED
test_kafka_repository.py::test_publish_batch PASSED
test_kafka_repository.py::test_publish_with_enrichment PASSED
test_kafka_repository.py::test_publish_handles_errors_gracefully PASSED

test_ingestion_service.py::test_start_stream PASSED
test_ingestion_service.py::test_stop_stream PASSED
test_ingestion_service.py::test_get_stream_status PASSED
test_ingestion_service.py::test_multiple_concurrent_streams PASSED
test_ingestion_service.py::test_fetch_historical_data PASSED
test_ingestion_service.py::test_stream_receives_data PASSED
test_ingestion_service.py::test_stop_nonexistent_stream PASSED
test_ingestion_service.py::test_tenant_isolation PASSED

=================== 19 passed in 45.23s ===================
```

## Troubleshooting

### PostgreSQL Connection Error

```
psycopg2.OperationalError: could not connect to server
```

**Solution**: Ensure PostgreSQL is running:
```bash
docker compose ps postgres
docker compose up -d postgres
```

### Kafka Connection Error

```
kafka.errors.NoBrokersAvailable
```

**Solution**: Ensure Kafka is running:
```bash
docker compose ps kafka
docker compose up -d kafka
```

### Database Not Found

```
psycopg2.OperationalError: database "crypto_dashboard" does not exist
```

**Solution**: Create the database:
```bash
docker exec -i crypto-postgres psql -U postgres -c "CREATE DATABASE crypto_dashboard;"
```

### Table Does Not Exist

```
psycopg2.errors.UndefinedTable: relation "stream_sessions" does not exist
```

**Solution**: Apply the schema:
```bash
docker exec -i crypto-postgres psql -U postgres -d crypto_dashboard < ingestion-service/tests/setup_test_db.sql
```

### Import Errors

```
ModuleNotFoundError: No module named 'repositories'
```

**Solution**: Make sure you're running from the project root and the **ingestion-service venv** is activated:
```bash
cd /Users/yuyu/workspace/crypto-dashboard
source ingestion-service/venv/bin/activate
python -m pytest ingestion-service/tests/ -v
```

## Quick Setup Script

Run this complete setup:

```bash
#!/bin/bash
cd /Users/yuyu/workspace/crypto-dashboard

# Start infrastructure
docker compose up -d postgres kafka

# Wait for services
echo "Waiting for services to be ready..."
sleep 5

# Create database
docker exec -i crypto-postgres psql -U postgres -c "CREATE DATABASE IF NOT EXISTS crypto_dashboard;"

# Apply schema
docker exec -i crypto-postgres psql -U postgres -d crypto_dashboard < ingestion-service/tests/setup_test_db.sql

# Activate ingestion-service venv
source ingestion-service/venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio psycopg2-binary

# Run tests
python -m pytest ingestion-service/tests/ -v -s
```

## CI/CD Integration

These tests are automatically run in the GitHub Actions workflow on every push and pull request.

See `.github/workflows/ci.yml` for the CI configuration.
