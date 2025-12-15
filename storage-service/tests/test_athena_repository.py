from unittest.mock import MagicMock

import pytest
from repositories.athena_repository import AthenaRepository


@pytest.mark.asyncio
class TestAthenaRepository:
    async def test_create_external_table(self, mock_athena_client):
        repo = AthenaRepository(mock_athena_client, "primary", "s3://results")
        mock_athena_client.get_query_execution.return_value = {
            "QueryExecution": {"Status": {"State": "SUCCEEDED"}}
        }

        result = await repo.create_external_table(
            "test_table", "s3://data", {"col1": "string"}, "db"
        )

        assert result is True
        mock_athena_client.start_query_execution.assert_called_once()
        assert (
            "CREATE EXTERNAL TABLE"
            in mock_athena_client.start_query_execution.call_args[1]["QueryString"]
        )

    async def test_execute_query(self, mock_athena_client):
        repo = AthenaRepository(mock_athena_client, "primary", "s3://results")

        exec_id = await repo.execute_query("SELECT 1")

        assert exec_id == "test-execution-id"
        mock_athena_client.start_query_execution.assert_called_once()

    async def test_wait_for_query_success(self, mock_athena_client):
        repo = AthenaRepository(mock_athena_client, "primary", "s3://results")

        status = await repo.wait_for_query("id", timeout=1, poll_interval=0.1)

        assert status == "SUCCEEDED"

    async def test_get_query_results(self, mock_athena_client):
        repo = AthenaRepository(mock_athena_client, "primary", "s3://results")

        results = await repo.get_query_results("id")

        assert results["row_count"] == 1
        assert results["rows"][0]["col1"] == "value1"
