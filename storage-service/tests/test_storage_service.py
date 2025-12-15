from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
class TestStorageService:
    async def test_archive_data_success(
        self,
        storage_service,
        mock_clickhouse_repository,
        mock_postgres_repository,
        mock_athena_client,
    ):
        # mock_athena_repository.wait_for_query will return "SUCCEEDED" because mock_athena_client returns success status

        result = await storage_service.archive_data(
            "tenant-1", datetime.utcnow(), datetime.utcnow(), "market_data"
        )

        assert result["success"] is True
        mock_postgres_repository.create_archive_job.assert_called_once()
        mock_postgres_repository.update_archive_job.assert_called()
        mock_clickhouse_repository.export_data_range.assert_called_once()
        mock_athena_client.start_query_execution.assert_called()

    async def test_query_archive_success(self, storage_service, mock_athena_client):
        result = await storage_service.query_archive(
            "tenant-1", "SELECT * FROM market_data", 100
        )

        assert result["row_count"] == 1
        mock_athena_client.start_query_execution.assert_called()
        assert (
            "SELECT * FROM market_data"
            in mock_athena_client.start_query_execution.call_args[1]["QueryString"]
        )

    async def test_get_archive_status(self, storage_service, mock_postgres_repository):
        status = await storage_service.get_archive_status("job-123")

        assert status["status"] == "completed"
        mock_postgres_repository.get_archive_job.assert_called_with("job-123")
