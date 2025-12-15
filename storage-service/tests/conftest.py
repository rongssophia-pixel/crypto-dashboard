"""
Pytest configuration and fixtures for Storage Service tests
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import boto3
from config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def localstack_session():
    """Session for LocalStack"""
    return boto3.Session(
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


@pytest.fixture(scope="session")
def real_s3_client(localstack_session):
    """Real S3 client pointing to LocalStack"""
    return localstack_session.client("s3", endpoint_url=settings.aws_endpoint_url)


@pytest.fixture(scope="session")
def real_athena_client(localstack_session):
    """Real Athena client pointing to LocalStack"""
    return localstack_session.client("athena", endpoint_url=settings.aws_endpoint_url)


@pytest.fixture
def mock_s3_client():
    """Mock S3 client"""
    client = MagicMock()
    # Setup default behaviors
    client.upload_file = MagicMock()
    client.put_object = MagicMock()
    client.list_objects_v2 = MagicMock(return_value={})
    client.head_object = MagicMock(return_value={})
    client.delete_object = MagicMock()
    return client


@pytest.fixture
def mock_athena_client():
    """Mock Athena client"""
    client = MagicMock()
    # Setup default behaviors
    client.start_query_execution = MagicMock(
        return_value={"QueryExecutionId": "test-execution-id"}
    )
    client.get_query_execution = MagicMock(
        return_value={"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}
    )
    client.get_query_results = MagicMock(
        return_value={
            "ResultSet": {
                "ResultSetMetadata": {"ColumnInfo": [{"Name": "col1"}]},
                "Rows": [
                    {"Data": [{"VarCharValue": "header"}]},
                    {"Data": [{"VarCharValue": "value1"}]},
                ],
            }
        }
    )
    return client


@pytest.fixture
def mock_s3_repository(mock_s3_client):
    from repositories.s3_repository import S3Repository

    repo = S3Repository(mock_s3_client, "test-bucket")
    return repo


@pytest.fixture
def mock_athena_repository(mock_athena_client):
    from repositories.athena_repository import AthenaRepository

    repo = AthenaRepository(mock_athena_client, "primary", "s3://results")
    return repo


@pytest.fixture
def mock_clickhouse_repository():
    # Use MagicMock directly as we dynamically import it in main but in tests we might not have the module loaded same way
    # Or we can mock the class structure
    repo = MagicMock()
    repo.export_data_range = MagicMock()

    async def async_iter(*args, **kwargs):
        yield [{"col1": "val1"}]

    repo.export_data_range.side_effect = async_iter
    return repo


@pytest.fixture
def mock_postgres_repository():
    repo = AsyncMock()
    repo.create_archive_job.return_value = "job-123"
    repo.update_archive_job.return_value = True
    repo.get_archive_job.return_value = {
        "archive_id": "job-123",
        "status": "completed",
        "s3_path": "s3://bucket/path",
        "records_archived": 100,
        "created_at": datetime.utcnow(),
        "completed_at": datetime.utcnow(),
    }
    repo.list_archive_jobs.return_value = []
    return repo


@pytest.fixture
def storage_service(
    mock_s3_repository,
    mock_athena_repository,
    mock_clickhouse_repository,
    mock_postgres_repository,
):
    from services.storage_service import StorageBusinessService

    return StorageBusinessService(
        mock_s3_repository,
        mock_athena_repository,
        mock_clickhouse_repository,
        mock_postgres_repository,
    )
